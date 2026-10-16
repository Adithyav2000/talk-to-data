"""Claimsight  --  FastAPI backend."""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import threading
import io
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pydantic import BaseModel

import config
import report_cache
import sql_assets
from data_service import DataService
from genie_client import GenieClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================================================================
# App
# ======================================================================
app = FastAPI(title="Claimsight")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ======================================================================
# Service singletons
# ======================================================================
_lock = threading.Lock()
_genie: GenieClient | None = None
_data_svc: DataService | None = None


class ServiceUnavailable(RuntimeError):
    pass


def get_genie() -> GenieClient:
    global _genie
    with _lock:
        if _genie is None:
            try:
                _genie = GenieClient(config.GENIE_SPACE_ID)
            except Exception as exc:
                raise ServiceUnavailable(f"Databricks is not configured: {exc}") from exc
        return _genie


def get_data_svc() -> DataService:
    global _data_svc
    with _lock:
        if _data_svc is None:
            try:
                svc = DataService()
            except Exception as exc:
                raise ServiceUnavailable(f"Databricks is not configured: {exc}") from exc
            svc.ensure_tables_exist()
            _data_svc = svc
        return _data_svc


@app.exception_handler(ServiceUnavailable)
def _service_unavailable(_request, exc: ServiceUnavailable):
    return JSONResponse(status_code=503, content={"error": str(exc)})


# ======================================================================
# Request models
# ======================================================================
class LoginRequest(BaseModel):
    username: str
    password: str


class ExecuteDataCallRequest(BaseModel):
    category: str | None = None
    dataCallId: int
    fromDate: str
    toDate: str
    refresh: bool = False


class SubmitRequest(BaseModel):
    description: str
    category: str | None = None


class SetStateRequest(BaseModel):
    category: str
    dataCallId: int
    state: str


class ReportRequest(BaseModel):
    prompt: str
    conversationId: str | None = None
    refresh: bool = False
    history: list[str] = []  # earlier questions in this Ask Data conversation


class GenerateSqlRequest(BaseModel):
    description: str
    conversationId: str | None = None


class ApproveRequest(BaseModel):
    requestId: int
    sqlQuery: str
    dataCallName: str
    description: str
    state: str
    category: str = "Compliance"


NUMBER_FORMATS = {
    "general": "General",
    "integer": "#,##0",
    "decimal": "#,##0.00",
    "currency": "$#,##0.00",
    "percent": "0.00%",
}


class ExportRequest(BaseModel):
    columns: list[str]
    rows: list[list]
    title: str = "Data"
    sql: str | None = None
    numberFormat: str = "general"      # key of NUMBER_FORMATS, applied to numeric columns
    styledHeader: bool = True
    freezeHeader: bool = True
    autoFilter: bool = True
    zebra: bool = False
    includeSql: bool = False


class CheckSqlRequest(BaseModel):
    sql: str


class SyncItem(BaseModel):
    category: str
    dataCallId: int


class SyncRequest(BaseModel):
    items: list[SyncItem] | None = None  # None = everything that is out of sync


class RejectRequest(BaseModel):
    requestId: int
    notes: str = ""


# ======================================================================
# Sessions  --  HMAC-signed bearer tokens (no server-side state)
# ======================================================================
_SECRET = (config.APP_SECRET or secrets.token_hex(32)).encode()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(txt: str) -> bytes:
    return base64.urlsafe_b64decode(txt + "=" * (-len(txt) % 4))


def _sign(body: str) -> str:
    return _b64(hmac.new(_SECRET, body.encode(), hashlib.sha256).digest())


def make_token(username: str) -> str:
    payload = {"u": username, "exp": int(time.time()) + config.SESSION_HOURS * 3600}
    body = _b64(json.dumps(payload).encode())
    return f"{body}.{_sign(body)}"


def read_token(token: str) -> str | None:
    try:
        body, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(body)):
            return None
        payload = json.loads(_unb64(body))
        return payload["u"] if payload["exp"] >= time.time() else None
    except Exception:
        return None


def public_user(username: str) -> dict:
    p = config.PERSONAS[username]
    return {
        "username": username,
        "name": p["name"],
        "role": p["role"],
        "title": p["title"],
        "icon": p["icon"],
        "accent": p["accent"],
        "tagline": p["tagline"],
        "permissions": p["permissions"],
        "registries": p["registries"],
        "kpis": p["kpis"],
        "quickActions": p["quickActions"],
        "pages": [
            page for page, perm in config.PAGE_PERMISSIONS.items()
            if perm is None or perm in p["permissions"]
        ],
    }


def current_user(authorization: str | None = Header(default=None)) -> dict:
    token = (authorization or "").removeprefix("Bearer ").strip()
    username = read_token(token) if token else None
    if not username or username not in config.PERSONAS:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    return public_user(username)


def needs(permission: str):
    def dep(user: dict = Depends(current_user)) -> dict:
        if permission not in user["permissions"]:
            raise HTTPException(status_code=403, detail="Your persona does not have access to this area.")
        return user
    return dep


# ======================================================================
# Helpers
# ======================================================================
def _ensure_data(res: dict) -> dict:
    """If Genie returned SQL but no tabular rows, execute SQL directly."""
    if res.get("columns") and res.get("rows"):
        return res
    sql = res.get("sql")
    if not sql:
        return res
    result = get_data_svc().execute_sql(sql)
    if "columns" in result and result.get("rows"):
        res["columns"] = result["columns"]
        res["rows"] = result["rows"]
    return res


def _cached_ask(prompt: str, conversation_id: str | None, refresh: bool,
                history: list[str] | None = None) -> dict:
    """Ask Genie, reusing a recent answer to the same question in the same context.

    `history` is the earlier questions of an Ask Data conversation. It makes a
    follow-up's cache key unique to its context, so follow-ups are cacheable too.
    Without history, a reply inside an existing conversation depends on Genie's
    server-side context and is never cached. Only successful tabular answers are
    stored; clarifying questions and errors are not. Cached copies carry no
    conversation id, so users never share (and pollute) a Genie conversation.
    """
    history = [h for h in (history or []) if h and h.strip()][-6:]
    if conversation_id and not history:
        return _ensure_data(get_genie().ask(prompt, conversation_id=conversation_id))

    key = report_cache.make_key("ask", *history, prompt)
    if not refresh and (hit := report_cache.get(key)):
        return hit

    if conversation_id or not history:
        res = _ensure_data(get_genie().ask(prompt, conversation_id=conversation_id))
    else:
        # A follow-up whose conversation was served from cache: rebuild the context.
        earlier = " ".join(f"({i}) {h}" for i, h in enumerate(history, 1))
        res = _ensure_data(get_genie().ask(
            f"Earlier questions in this conversation: {earlier}. Now answer this follow-up: {prompt}"
        ))
    if report_cache.cacheable(res):
        report_cache.put(key, {k: v for k, v in res.items() if k != "conversation_id"})
    return res


def _records(res: dict) -> list[dict]:
    cols = res.get("columns", [])
    return [dict(zip(cols, r)) for r in res.get("rows", [])]


def _registry(user: dict, category: str | None) -> str:
    """Resolve a requested registry, refusing any the persona may not use."""
    allowed = user["registries"]
    category = category or allowed[0]
    if category not in allowed:
        raise HTTPException(status_code=403, detail=f"Your persona cannot access the {category} registry.")
    return category


def _in_scope(req: dict, user: dict) -> bool:
    # Requests logged before registries were scoped have no category: they were Compliance.
    return (req.get("category") or "Compliance") in user["registries"]


def _ts(value) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _days(a: datetime | None, b: datetime | None) -> float | None:
    return round((b - a).total_seconds() / 86400, 1) if a and b else None


def _review_stats(reqs: list[dict]) -> dict:
    """Turnaround and ageing figures for a set of IT requests."""
    now = datetime.now(timezone.utc)
    turnarounds = [
        t for r in reqs
        if str(r.get("status")).lower() in ("approved", "rejected")
        and (t := _days(_ts(r.get("requested_at")), _ts(r.get("reviewed_at")))) is not None
    ]
    ages = [
        a for r in reqs
        if str(r.get("status")).lower() == "pending"
        and (a := _days(_ts(r.get("requested_at")), now)) is not None
    ]
    return {
        "avgReviewDays": round(sum(turnarounds) / len(turnarounds), 1) if turnarounds else None,
        "oldestPendingDays": round(max(ages)) if ages else 0,
    }


def _load_calls(svc: DataService, user: dict, warnings: list[str]) -> list[dict]:
    calls: list[dict] = []
    for category in user["registries"]:
        res = svc.get_data_calls(table=config.DATA_CALL_CATEGORIES[category])
        if "error" in res:
            warnings.append(f"{category} registry: {res['error']}")
            continue
        for rec in _records(res):
            rec["category"] = category
            calls.append(rec)
    return calls


# ======================================================================
# SPA entry
# ======================================================================
@app.get("/")
def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"), headers={"Cache-Control": "no-cache"})


# ======================================================================
# Auth
# ======================================================================
@app.get("/api/personas")
def list_personas():
    """Public, password-free list that drives the sign-in screen."""
    keep = ("username", "name", "title", "icon", "accent", "tagline", "permissions", "registries", "pages")
    return {
        "personas": [
            {k: v for k, v in public_user(u).items() if k in keep}
            for u in config.PERSONAS
        ],
        "demoHint": config.DEMO_PASSWORD if config.DEMO_PASSWORD == "admin" else "",
    }


@app.post("/api/auth/login")
def login(req: LoginRequest):
    persona = config.PERSONAS.get(req.username)
    if persona and hmac.compare_digest(persona["password"].encode(), req.password.encode()):
        return {"success": True, "token": make_token(req.username), "user": public_user(req.username)}
    return {"success": False, "error": "That password is not correct."}


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return {"user": user}


# ======================================================================
# Dashboard
# ======================================================================
@app.get("/api/dashboard")
def dashboard(user: dict = Depends(current_user)):
    svc = get_data_svc()
    warnings: list[str] = []

    calls = _load_calls(svc, user, warnings)

    scope_all = "see_all_requests" in user["permissions"]
    reqs_res = svc.get_it_requests(requested_by=None if scope_all else user["username"])
    if "error" in reqs_res:
        warnings.append(f"Request log: {reqs_res['error']}")
    reqs = [r for r in _records(reqs_res) if _in_scope(r, user)]

    if warnings and not calls and not reqs:
        return JSONResponse(status_code=502, content={"error": " | ".join(warnings)})

    by_state = Counter((c.get("state") or "NA") for c in calls)
    by_status = Counter(str(r.get("status") or "").lower() for r in reqs)
    tested = by_state["TESTED_PASS"] + by_state["TESTED_FAIL"]
    mine = [r for r in reqs if r.get("requested_by") == user["username"]]

    return {
        "metrics": {
            "totalCalls": len(calls),
            "passRate": round(100 * by_state["TESTED_PASS"] / tested) if tested else None,
            "pendingReviews": by_status["pending"],
            "totalRequests": len(reqs),
            "approvedCount": by_status["approved"],
            "rejectedCount": by_status["rejected"],
            "myRequests": len(mine),
            "myPending": sum(1 for r in mine if str(r.get("status")).lower() == "pending"),
            "reportCategories": len(config.REPORT_PROMPTS),
            "needsAttention": by_state["TESTED_FAIL"] + by_state["NA"],
            **_review_stats(reqs),
        },
        "stateBreakdown": dict(by_state),
        "categoryBreakdown": dict(Counter(c["category"] for c in calls)),
        "requestStatus": dict(by_status),
        "recentCalls": sorted(calls, key=lambda c: int(c.get("data_call_id") or 0), reverse=True)[:6],
        "recentRequests": reqs[:6],
        "scope": "all" if scope_all else "mine",
        "warnings": warnings,
    }


# ======================================================================
# Data Calls
# ======================================================================
@app.get("/api/data-calls/categories")
def data_call_categories(user: dict = Depends(needs("data_calls"))):
    return {"categories": user["registries"]}


@app.get("/api/data-calls")
def get_data_calls(category: str | None = None, state: str = "All", search: str = "",
                   user: dict = Depends(needs("data_calls"))):
    table = config.DATA_CALL_CATEGORIES[_registry(user, category)]
    if state not in config.DATA_CALL_STATES:
        state = "All"
    res = get_data_svc().get_data_calls(table=table, state=state, name_search=search or None)
    return {"records": _records(res), "error": res.get("error")}


@app.post("/api/data-calls/execute")
def execute_data_call(req: ExecuteDataCallRequest, user: dict = Depends(needs("data_calls"))):
    """Run a registered data call: load its SQL asset, apply the period, run it on the warehouse."""
    category = _registry(user, req.category)
    table = config.DATA_CALL_CATEGORIES[category]
    try:
        start, end = sql_assets.parse_period(req.fromDate, req.toDate)
    except sql_assets.SqlAssetError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    key = report_cache.make_key("call", category, str(req.dataCallId), start, end)
    if not req.refresh and (hit := report_cache.get(key)):
        return hit

    svc = get_data_svc()
    try:
        asset = svc.get_data_call_asset(table, req.dataCallId)
    except RuntimeError as exc:
        return JSONResponse(status_code=502, content={"error": str(exc)})
    if not asset:
        return JSONResponse(status_code=404, content={"error": "That data call is not in the registry."})

    sql = svc.get_data_call_sql(asset["asset_location"])
    source = asset["asset_location"] or asset["file_name"]
    if not sql:
        sql = svc.get_approved_sql(asset["file_name"])  # calls registered through IT review
        source = f"approved request ({asset['file_name']})"
    if not sql:
        return JSONResponse(status_code=404, content={
            "error": f"No SQL file could be loaded for “{asset['name']}”"
                     + (f" from {asset['asset_location']}." if asset["asset_location"] else " (the registry has no asset location).")
        })

    try:
        final_sql, mode, replaced = sql_assets.apply_period(sql, start, end)
    except sql_assets.SqlAssetError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    res = svc.execute_sql(final_sql)
    if "error" in res:
        return JSONResponse(status_code=502, content={"error": res["error"], "sql": final_sql})
    out = {**res, "sql": final_sql, "dateMode": mode, "replaced": replaced,
           "source": source, "period": [start, end]}
    if report_cache.cacheable(out):
        report_cache.put(key, out)
    return out


@app.post("/api/data-calls/request")
def submit_data_call_request(req: SubmitRequest, user: dict = Depends(needs("data_calls"))):
    category = _registry(user, req.category)
    try:
        out = get_data_svc().submit_request(req.description, user["username"], category)
    except RuntimeError as exc:
        return JSONResponse(status_code=502, content={"error": str(exc)})
    return {
        "isNew": out["is_new"],
        "matchedName": out["matched_name"],
        "similarityScore": out["similarity_score"],
    }


@app.get("/api/data-calls/my-requests")
def my_requests(user: dict = Depends(needs("data_calls"))):
    res = get_data_svc().get_it_requests(requested_by=user["username"])
    return {"records": [r for r in _records(res) if _in_scope(r, user)], "error": res.get("error")}


# ======================================================================
# Governance  (Admin control tower)
# ======================================================================
@app.get("/api/governance")
def governance(category: str | None = None, user: dict = Depends(needs("governance"))):
    svc = get_data_svc()
    warnings: list[str] = []
    # Optionally narrow to one registry; everything below uses the narrowed view.
    view = {**user, "registries": [_registry(user, category)] if category else user["registries"]}
    calls = _load_calls(svc, view, warnings)
    reqs_res = svc.get_it_requests()
    if "error" in reqs_res:
        warnings.append(f"Request log: {reqs_res['error']}")
    reqs = [r for r in _records(reqs_res) if _in_scope(r, view)]
    if warnings and not calls and not reqs:
        return JSONResponse(status_code=502, content={"error": " | ".join(warnings)})

    now = datetime.now(timezone.utc)
    by_state = Counter((c.get("state") or "NA") for c in calls)
    tested = by_state["TESTED_PASS"] + by_state["TESTED_FAIL"]

    # Failing first, then untested: the retest queue.
    order = {"TESTED_FAIL": 0, "NA": 1}
    attention = sorted(
        (c for c in calls if (c.get("state") or "NA") in order),
        key=lambda c: (order[c.get("state") or "NA"], str(c.get("data_call_name"))),
    )

    pending = []
    for r in reqs:
        if str(r.get("status")).lower() != "pending":
            continue
        age = _days(_ts(r.get("requested_at")), now)
        pending.append({**r, "ageDays": age, "overdue": age is not None and age > config.REVIEW_SLA_DAYS})
    pending.sort(key=lambda r: -(r["ageDays"] or 0))

    decided = [r for r in reqs if str(r.get("status")).lower() in ("approved", "rejected")]
    audit = [
        {**r, "turnaroundDays": _days(_ts(r.get("requested_at")), _ts(r.get("reviewed_at")))}
        for r in sorted(decided, key=lambda r: str(r.get("reviewed_at") or ""), reverse=True)[:15]
    ]

    # Demand signal: existing calls people keep asking for something like.
    demand = Counter(r["matched_data_call"] for r in reqs if r.get("matched_data_call"))

    return {
        "registries": user["registries"],
        "selected": category,
        "scorecard": {
            "total": len(calls),
            "passing": by_state["TESTED_PASS"],
            "failing": by_state["TESTED_FAIL"],
            "untested": by_state["NA"],
            "passRate": round(100 * by_state["TESTED_PASS"] / tested) if tested else None,
            "coverage": round(100 * tested / len(calls)) if calls else None,
        },
        "attention": attention,
        "pending": pending,
        "audit": audit,
        "demand": [{"name": n, "requests": c} for n, c in demand.most_common(6)],
        "stats": _review_stats(reqs),
        "slaDays": config.REVIEW_SLA_DAYS,
        "warnings": warnings,
    }


@app.post("/api/governance/set-state")
def governance_set_state(req: SetStateRequest, user: dict = Depends(needs("governance"))):
    table = config.DATA_CALL_CATEGORIES[_registry(user, req.category)]
    try:
        get_data_svc().set_call_state(table, req.dataCallId, req.state)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ======================================================================
# Enterprise Reports / Ask Data
# ======================================================================
@app.get("/api/reports/categories")
def report_categories(user: dict = Depends(needs("reports"))):
    return {"categories": config.REPORT_PROMPTS}


@app.post("/api/reports/generate")
def generate_report(req: ReportRequest, user: dict = Depends(needs("reports"))):
    return _cached_ask(req.prompt, req.conversationId, req.refresh, req.history)


# ======================================================================
# Export
# ======================================================================
_NON_NUMERIC_NAME = re.compile(r"(^|_)(id|zip|code|number|no)$|date|month|year|quarter|week|day|time|period", re.I)


def _num(v):
    if v is None or v == "" or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() and "." not in str(v) and "e" not in str(v).lower() else f


@app.post("/api/export/xlsx")
def export_xlsx(req: ExportRequest, user: dict = Depends(current_user)):
    if len(req.rows) > 200_000:
        raise HTTPException(status_code=413, detail="Too many rows to export.")
    fmt = NUMBER_FORMATS.get(req.numberFormat, "General")
    wb = Workbook()
    ws = wb.active
    ws.title = (re.sub(r"[\/*?:\[\]]", " ", req.title).strip() or "Data")[:31]

    cols = req.columns
    numeric = []
    for i, c in enumerate(cols):
        vals = [r[i] for r in req.rows if i < len(r) and r[i] not in (None, "")]
        numeric.append(bool(vals) and not _NON_NUMERIC_NAME.search(c)
                       and sum(_num(v) is not None for v in vals) / len(vals) >= 0.9)

    ws.append([c.replace("_", " ").title() for c in cols])
    for r in req.rows:
        ws.append([(_num(r[i]) if numeric[i] and _num(r[i]) is not None else r[i]) if i < len(r) else None
                   for i in range(len(cols))])

    if req.styledHeader:
        fill = PatternFill("solid", fgColor="1F7A5C")
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = fill
            cell.alignment = Alignment(vertical="center")
        ws.row_dimensions[1].height = 22
    else:
        for cell in ws[1]:
            cell.font = Font(bold=True)
    if req.zebra:
        band = PatternFill("solid", fgColor="F1F6F3")
        for row in ws.iter_rows(min_row=2):
            if row[0].row % 2 == 1:
                for cell in row:
                    cell.fill = band
    if fmt != "General":
        for i, is_num in enumerate(numeric, start=1):
            if is_num:
                for cell in ws.iter_cols(min_col=i, max_col=i, min_row=2).__next__():
                    cell.number_format = fmt
    for i, c in enumerate(cols, start=1):
        longest = max([len(str(c))] + [len(str(r[i - 1])) for r in req.rows[:500] if i - 1 < len(r) and r[i - 1] is not None])
        ws.column_dimensions[get_column_letter(i)].width = min(max(longest + 3, 10), 60)
    if req.freezeHeader:
        ws.freeze_panes = "A2"
    if req.autoFilter and req.rows:
        ws.auto_filter.ref = ws.dimensions

    if req.includeSql and req.sql:
        sq = wb.create_sheet("SQL")
        sq.column_dimensions["A"].width = 120
        for line in req.sql.splitlines() or [req.sql]:
            sq.append([line])
            sq.cell(row=sq.max_row, column=1).font = Font(name="Consolas", size=10)

    buf = io.BytesIO()
    wb.save(buf)
    fname = re.sub(r"[^\w-]+", "_", req.title).strip("_") or "export"
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}.xlsx"'},
    )


# ======================================================================
# IT Review
# ======================================================================
@app.get("/api/it-review")
def get_it_requests(status: str = "All", user: dict = Depends(needs("it_review"))):
    res = get_data_svc().get_it_requests(status)
    return {"records": _records(res), "error": res.get("error")}


@app.post("/api/it-review/generate-sql")
def generate_sql(req: GenerateSqlRequest, user: dict = Depends(needs("it_review"))):
    return _ensure_data(get_genie().ask(req.description, conversation_id=req.conversationId))


@app.post("/api/it-review/check-sql")
def check_sql(req: CheckSqlRequest, user: dict = Depends(needs("it_review"))):
    """Tell a reviewer whether SQL is runnable as a data call and how a date range will apply."""
    try:
        _, mode, replaced = sql_assets.apply_period(req.sql, "2000-01-01", "2000-12-31")
    except sql_assets.SqlAssetError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "dateMode": mode, "replaced": replaced}


@app.post("/api/it-review/approve")
def approve_request(req: ApproveRequest, user: dict = Depends(needs("it_review"))):
    try:
        sql_assets.check_read_only(req.sqlQuery)
    except sql_assets.SqlAssetError as exc:
        return {"success": False, "error": str(exc)}
    table = config.DATA_CALL_CATEGORIES.get(req.category)
    if not table:
        return {"success": False, "error": f"Unknown category: {req.category}"}
    try:
        get_data_svc().approve_request(
            req.requestId, user["username"],
            req.sqlQuery, req.dataCallName, req.description, req.state, table,
        )
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.get("/api/it-review/unsynced")
def unsynced_calls(user: dict = Depends(needs("it_review"))):
    try:
        return {"items": get_data_svc().list_unsynced()}
    except RuntimeError as exc:
        return JSONResponse(status_code=502, content={"error": str(exc)})


@app.post("/api/it-review/sync")
def sync_registry(req: SyncRequest, user: dict = Depends(needs("it_review"))):
    """Write SQL files for approved data calls that have none and link them in the registry."""
    svc = get_data_svc()
    try:
        pending = svc.list_unsynced()
    except RuntimeError as exc:
        return JSONResponse(status_code=502, content={"error": str(exc)})
    if req.items is not None:
        wanted = {(i.category, i.dataCallId) for i in req.items}
        pending = [p for p in pending if (p["category"], p["dataCallId"]) in wanted]
    results = svc.sync_to_registry(pending, user["username"])
    if any(r["ok"] for r in results):
        report_cache.clear()  # a synced call now runs from its file
    return {"results": results, "synced": sum(1 for r in results if r["ok"]), "failed": sum(1 for r in results if not r["ok"])}


@app.post("/api/it-review/reject")
def reject_request(req: RejectRequest, user: dict = Depends(needs("it_review"))):
    try:
        get_data_svc().reject_request(req.requestId, user["username"], req.notes)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ======================================================================
# Config endpoints
# ======================================================================
@app.get("/api/config/states")
def get_states(user: dict = Depends(current_user)):
    return {"states": config.DATA_CALL_STATES}
