"""Prepare a registry data call's SQL asset for execution.

A data call's SQL lives in a file (the registry's `asset_location`). To run it
for a chosen period we:

  1. substitute date placeholders  (:from_date, {{from_date}}, ${from_date}, {from_date} ...)
  2. otherwise, if the file filters on a year (YEAR(c.accident_date) >= 2020), rewrite
     that filter into a real date range on the same column
  3. otherwise, if the file hard-codes two or more ISO date literals ('2020-01-01'),
     treat the earliest as the period start and the latest as the period end
  4. otherwise, if the file is relative to today (CURRENT_DATE, CURRENT_TIMESTAMP, NOW()),
     run it "as of" the period end: today is replaced by the end date, so a query for
     "this quarter" returns the quarter that contains the end date
  5. otherwise run it exactly as written

The query is also checked to be a single read-only SELECT / WITH statement,
because it is executed with the app's warehouse permissions.
"""

import re
from datetime import date

FROM_NAMES = ("from_date", "start_date", "date_from", "begin_date", "fromdate", "startdate")
TO_NAMES = ("to_date", "end_date", "date_to", "thru_date", "todate", "enddate")

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|merge|alter|create|truncate|grant|revoke|copy|optimize|vacuum|call|use)\b",
    re.I,
)
_LITERAL = re.compile(r"'(?:[^']|'')*'")
_DATE_LITERAL = re.compile(r"(?<![\w.])((?:DATE\s*)?)'(\d{4}-\d{2}-\d{2})'", re.I)


# YEAR(col) <op> 2020   and   YEAR(col) BETWEEN 2020 AND 2023
_YEAR_FILTER = re.compile(
    r"YEAR\(\s*(?P<col>[\w.]+)\s*\)\s*(?:BETWEEN\s+\d{4}\s+AND\s+\d{4}|(?:>=|<=|<>|!=|>|<|=)\s*\d{4})",
    re.I,
)


# CURRENT_DATE, current_date(), CURDATE(), TODAY()  /  CURRENT_TIMESTAMP, NOW()
_TODAY = re.compile(r"\b(?:current_date|curdate|today)\b(?:\s*\(\s*\))?", re.I)
_NOW = re.compile(r"\b(?:current_timestamp|now)\b(?:\s*\(\s*\))?", re.I)


class SqlAssetError(ValueError):
    """The SQL asset cannot be run safely or the period is invalid."""


def _placeholder_re(names: tuple[str, ...]) -> re.Pattern:
    alt = "|".join(re.escape(n) for n in names)
    return re.compile(
        rf"(?<!:):(?:{alt})\b"            # :from_date   (not the :: cast operator)
        rf"|\{{\{{\s*(?:{alt})\s*\}}\}}"  # {{from_date}}
        rf"|\$\{{\s*(?:{alt})\s*\}}"      # ${from_date}
        rf"|\{{\s*(?:{alt})\s*\}}",       # {from_date}
        re.I,
    )


def _substitute(sql: str, pattern: re.Pattern, value: str) -> tuple[str, int]:
    """Replace placeholders with a date, without doubling quotes the file already has."""
    count = 0
    out, last = [], 0
    for m in pattern.finditer(sql):
        before = sql[m.start() - 1] if m.start() else ""
        after = sql[m.end()] if m.end() < len(sql) else ""
        quoted = before == "'" and after == "'"
        out.append(sql[last:m.start()])
        out.append(value if quoted else f"DATE'{value}'")
        last = m.end()
        count += 1
    out.append(sql[last:])
    return "".join(out), count


def _rewrite_year_filters(sql: str, start: str, end: str) -> tuple[str, int]:
    """Turn `YEAR(col) >= 2020` style filters into a date range on the same column.

    The first YEAR(col) predicate for a column becomes the whole range; any further
    YEAR(col) predicates on that column (e.g. an upper bound) are neutralised to 1=1,
    which assumes they are ANDed with the rest of the WHERE clause.
    """
    seen: set[str] = set()
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        col = m.group("col")
        count += 1
        if col.lower() in seen:
            return "1=1"
        seen.add(col.lower())
        # `< end + 1 day` keeps the end date inclusive for DATE and TIMESTAMP columns alike
        return f"({col} >= DATE'{start}' AND {col} < DATE_ADD(DATE'{end}', 1))"

    return _YEAR_FILTER.sub(repl, sql), count


def parse_period(from_date: str, to_date: str) -> tuple[str, str]:
    try:
        start, end = date.fromisoformat(from_date), date.fromisoformat(to_date)
    except (TypeError, ValueError):
        raise SqlAssetError("Choose a valid from and to date.") from None
    if start > end:
        raise SqlAssetError("The from date must be on or before the to date.")
    return start.isoformat(), end.isoformat()


def check_read_only(sql: str) -> str:
    """Return the statement without comments/trailing semicolons, or raise."""
    body = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    body = re.sub(r"--[^\n]*", " ", body).strip().rstrip(";").strip()
    if not body:
        raise SqlAssetError("The SQL file is empty.")
    bare = _LITERAL.sub("''", body)
    if ";" in bare:
        raise SqlAssetError("The SQL file contains more than one statement; only a single SELECT can be run.")
    if not re.match(r"(select|with)\b", bare, re.I) or _FORBIDDEN.search(bare):
        raise SqlAssetError("Only read-only SELECT queries can be run from a data call.")
    return body


def apply_period(sql: str, from_date: str, to_date: str) -> tuple[str, str, int]:
    """Return (sql, mode, replacements).

    mode is 'placeholders', 'year_filter', 'literals', 'as_of' or 'none'.
    """
    start, end = parse_period(from_date, to_date)
    body = check_read_only(sql)

    body, n_from = _substitute(body, _placeholder_re(FROM_NAMES), start)
    body, n_to = _substitute(body, _placeholder_re(TO_NAMES), end)
    if n_from + n_to:
        return body, "placeholders", n_from + n_to

    body, n_year = _rewrite_year_filters(body, start, end)
    if n_year:
        return body, "year_filter", n_year

    found = sorted({m.group(2) for m in _DATE_LITERAL.finditer(body)})
    if len(found) >= 2:
        lo, hi = found[0], found[-1]
        swap = {lo: start, hi: end}
        replaced = sum(1 for m in _DATE_LITERAL.finditer(body) if m.group(2) in swap)
        body = _DATE_LITERAL.sub(lambda m: f"{m.group(1)}'{swap.get(m.group(2), m.group(2))}'", body)
        return body, "literals", replaced
    as_of, n_today = _TODAY.subn(f"DATE'{end}'", body)
    as_of, n_now = _NOW.subn(f"TIMESTAMP'{end} 23:59:59'", as_of)
    if n_today + n_now:
        return as_of, "as_of", n_today + n_now
    return body, "none", 0
