"""Workers' Compensation Talk-to-Data  --  FastAPI Backend."""

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
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pydantic import BaseModel

import config
from data_service import DataService
from genie_client import GenieClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================================================================
# App
# ======================================================================
app = FastAPI(title="Workers' Comp Talk-to-Data")

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
    description: str
    fromDate: str = ""
    toDate: str = ""
    conversationId: str | None = None


class SubmitRequest(BaseModel):
    description: str


class ReportRequest(BaseModel):
    prompt: str
    conversationId: str | None = None


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


def _records(res: dict) -> list[dict]:
    cols = res.get("columns", [])
    return [dict(zip(cols, r)) for r in res.get("rows", [])]


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
    keep = ("username", "name", "title", "icon", "accent", "tagline", "permissions", "pages")
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

    calls: list[dict] = []
    for category, table in config.DATA_CALL_CATEGORIES.items():
        res = svc.get_data_calls(table=table)
        if "error" in res:
            warnings.append(f"{category} registry: {res['error']}")
            continue
        for rec in _records(res):
            rec["category"] = category
            calls.append(rec)

    scope_all = "see_all_requests" in user["permissions"]
    reqs_res = svc.get_it_requests(requested_by=None if scope_all else user["username"])
    if "error" in reqs_res:
        warnings.append(f"Request log: {reqs_res['error']}")
    reqs = _records(reqs_res)

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
    return {"categories": list(config.DATA_CALL_CATEGORIES.keys())}


@app.get("/api/data-calls")
def get_data_calls(category: str = "Compliance", state: str = "All", search: str = "",
                   user: dict = Depends(needs("data_calls"))):
    table = config.DATA_CALL_CATEGORIES.get(category, config.DATA_CALLS_TABLE)
    if state not in config.DATA_CALL_STATES:
        state = "All"
    res = get_data_svc().get_data_calls(table=table, state=state, name_search=search or None)
    return {"records": _records(res), "error": res.get("error")}


@app.post("/api/data-calls/execute")
def execute_data_call(req: ExecuteDataCallRequest, user: dict = Depends(needs("data_calls"))):
    # Dates only frame the first question; replies in a conversation are sent as typed.
    prompt = req.description if req.conversationId else f"{req.description} (from {req.fromDate} to {req.toDate})"
    return _ensure_data(get_genie().ask(prompt, conversation_id=req.conversationId))


@app.post("/api/data-calls/request")
def submit_data_call_request(req: SubmitRequest, user: dict = Depends(needs("data_calls"))):
    try:
        out = get_data_svc().submit_request(req.description, user["username"])
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
    return {"records": _records(res), "error": res.get("error")}


# ======================================================================
# Enterprise Reports / Ask Data
# ======================================================================
@app.get("/api/reports/categories")
def report_categories(user: dict = Depends(needs("reports"))):
    return {"categories": config.REPORT_PROMPTS}


@app.post("/api/reports/generate")
def generate_report(req: ReportRequest, user: dict = Depends(needs("reports"))):
    return _ensure_data(get_genie().ask(req.prompt, conversation_id=req.conversationId))


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


@app.post("/api/it-review/approve")
def approve_request(req: ApproveRequest, user: dict = Depends(needs("it_review"))):
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
