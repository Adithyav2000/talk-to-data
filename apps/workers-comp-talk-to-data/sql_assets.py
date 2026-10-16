"""Prepare a registry data call's SQL asset for execution.

A data call's SQL lives in a file (the registry's `asset_location`). To run it
for a chosen period we:

  1. substitute date placeholders  (:from_date, {{from_date}}, ${from_date}, {from_date} ...)
  2. otherwise, if the file hard-codes two or more ISO date literals ('2020-01-01'),
     treat the earliest as the period start and the latest as the period end
  3. otherwise run it exactly as written

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
    """Return (sql, mode, replacements). mode is 'placeholders', 'literals' or 'none'."""
    start, end = parse_period(from_date, to_date)
    body = check_read_only(sql)

    body, n_from = _substitute(body, _placeholder_re(FROM_NAMES), start)
    body, n_to = _substitute(body, _placeholder_re(TO_NAMES), end)
    if n_from + n_to:
        return body, "placeholders", n_from + n_to

    found = sorted({m.group(2) for m in _DATE_LITERAL.finditer(body)})
    if len(found) >= 2:
        lo, hi = found[0], found[-1]
        swap = {lo: start, hi: end}
        replaced = sum(1 for m in _DATE_LITERAL.finditer(body) if m.group(2) in swap)
        body = _DATE_LITERAL.sub(lambda m: f"{m.group(1)}'{swap.get(m.group(2), m.group(2))}'", body)
        return body, "literals", replaced
    return body, "none", 0
