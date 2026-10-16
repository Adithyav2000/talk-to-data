"""Workers' Compensation Talk-to-Data  --  FastAPI Backend."""

import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
from genie_client import GenieClient
from data_service import DataService

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
genie = GenieClient(config.GENIE_SPACE_ID)
data_svc = DataService()
data_svc.ensure_tables_exist()


# ======================================================================
# Pydantic request models
# ======================================================================
class LoginRequest(BaseModel):
    username: str
    password: str


class ExecuteDataCallRequest(BaseModel):
    description: str
    fromDate: str = ""
    toDate: str = ""


class SubmitRequest(BaseModel):
    description: str
    requestedBy: str = "unknown"


class ReportRequest(BaseModel):
    prompt: str
    conversationId: str | None = None


class GenerateSqlRequest(BaseModel):
    description: str


class ApproveRequest(BaseModel):
    requestId: int
    reviewer: str
    sqlQuery: str
    dataCallName: str
    description: str
    state: str


class RejectRequest(BaseModel):
    requestId: int
    reviewer: str
    notes: str = ""


# ======================================================================
# Helpers
# ======================================================================
def _ensure_data(res: dict) -> dict:
    """If Genie returned SQL but no tabular rows, execute SQL directly."""
    has_data = res.get("columns") and res.get("rows")
    if has_data:
        return res
    sql = res.get("sql")
    if not sql:
        return res
    result = data_svc.execute_sql(sql)
    if "columns" in result and result.get("rows"):
        res["columns"] = result["columns"]
        res["rows"] = result["rows"]
    return res


# ======================================================================
# SPA entry
# ======================================================================
@app.get("/")
async def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ======================================================================
# Auth
# ======================================================================
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = config.USERS.get(req.username)
    if user and user["password"] == req.password:
        return {
            "success": True,
            "name": user["name"],
            "role": user["role"],
            "username": req.username,
        }
    return {"success": False, "error": "Invalid credentials"}


# ======================================================================
# Dashboard
# ======================================================================
@app.get("/api/dashboard")
async def dashboard():
    calls = data_svc.get_data_calls()
    reqs = data_svc.get_it_requests()
    total_calls = len(calls.get("rows", []))
    total_reqs = len(reqs.get("rows", []))
    pending = sum(1 for r in reqs.get("rows", []) if "pending" in str(r).lower())
    return {
        "metrics": {
            "totalCalls": total_calls,
            "totalRequests": total_reqs,
            "pendingReviews": pending,
            "reportCategories": len(config.REPORT_PROMPTS),
        },
        "recentCalls": {
            "columns": calls.get("columns", []),
            "rows": calls.get("rows", [])[:5],
        },
        "recentRequests": {
            "columns": reqs.get("columns", []),
            "rows": reqs.get("rows", [])[:5],
        },
    }


# ======================================================================
# Data Calls
# ======================================================================
@app.get("/api/data-calls/categories")
async def data_call_categories():
    return {"categories": list(config.DATA_CALL_CATEGORIES.keys())}


@app.get("/api/data-calls")
async def get_data_calls(category: str = "Compliance", state: str = "All", search: str = ""):
    table = config.DATA_CALL_CATEGORIES.get(category, config.DATA_CALLS_TABLE)
    return data_svc.get_data_calls(table=table, state=state, name_search=search or None)


@app.post("/api/data-calls/execute")
async def execute_data_call(req: ExecuteDataCallRequest):
    prompt = f"{req.description} (from {req.fromDate} to {req.toDate})"
    res = genie.ask(prompt)
    res = _ensure_data(res)
    return res


@app.post("/api/data-calls/request")
async def submit_data_call_request(req: SubmitRequest):
    out = data_svc.submit_request(req.description, req.requestedBy)
    return {
        "isNew": out["is_new"],
        "matchedName": out["matched_name"],
        "similarityScore": out["similarity_score"],
    }


# ======================================================================
# Enterprise Reports
# ======================================================================
@app.get("/api/reports/categories")
async def report_categories():
    return {"categories": config.REPORT_PROMPTS}


@app.post("/api/reports/generate")
async def generate_report(req: ReportRequest):
    res = genie.ask(req.prompt, conversation_id=req.conversationId)
    res = _ensure_data(res)
    return res


# ======================================================================
# IT Review
# ======================================================================
@app.get("/api/it-review")
async def get_it_requests(status: str = "All"):
    return data_svc.get_it_requests(status)


@app.post("/api/it-review/generate-sql")
async def generate_sql(req: GenerateSqlRequest):
    res = genie.ask(req.description)
    res = _ensure_data(res)
    return res


@app.post("/api/it-review/approve")
async def approve_request(req: ApproveRequest):
    try:
        data_svc.approve_request(
            req.requestId, req.reviewer,
            req.sqlQuery, req.dataCallName, req.description, req.state,
        )
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.post("/api/it-review/reject")
async def reject_request(req: RejectRequest):
    try:
        data_svc.reject_request(req.requestId, req.reviewer, req.notes)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ======================================================================
# Config endpoints
# ======================================================================
@app.get("/api/config/states")
async def get_states():
    return {"states": config.DATA_CALL_STATES}
