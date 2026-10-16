import os
from pathlib import Path


def _load_dotenv():
    env_file = Path(__file__).parent / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# ---------------------------------------------------------------------------
# Genie Configuration
# ---------------------------------------------------------------------------
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "01f1c8b8bc9e187595404d6a66c18dc6")

# ---------------------------------------------------------------------------
# Unity Catalog tables
# ---------------------------------------------------------------------------
COMPLIANCE_CALLS_TABLE = "workers_comp_insurance.data_call_registry.compliance_data_calls"
FINANCIAL_CALLS_TABLE = "workers_comp_insurance.data_call_registry.financial_data_calls"
DATA_CALLS_TABLE = COMPLIANCE_CALLS_TABLE  # default
IT_REQUESTS_TABLE = "easewithdata_adb.bronze.it_review_requests"

DATA_CALL_CATEGORIES = {
    "Compliance": COMPLIANCE_CALLS_TABLE,
    "Financial Reporting": FINANCIAL_CALLS_TABLE,
}

# ---------------------------------------------------------------------------
# Semantic matching
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.65

# ---------------------------------------------------------------------------
# Personas  (replace with SSO / Databricks OAuth in production)
#
# Each persona declares what it may open (`permissions`), what its home screen
# emphasises (`kpis`, `quickActions`) and how it appears on the sign-in screen.
# Permissions are enforced server-side in main.py.
# ---------------------------------------------------------------------------
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "admin")
APP_SECRET = os.getenv("APP_SECRET", "")  # empty -> random per process
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))

# Report / data-call result cache
REPORT_CACHE_TTL_HOURS = float(os.getenv("REPORT_CACHE_TTL_HOURS", "24"))
REPORT_CACHE_MAX = int(os.getenv("REPORT_CACHE_MAX", "200"))

ALL_REGISTRIES = list(DATA_CALL_CATEGORIES.keys())

# Governance: a data call needs attention when it is failing or untested, and a
# pending request is overdue after this many days.
REVIEW_SLA_DAYS = int(os.getenv("REVIEW_SLA_DAYS", "3"))

# `registries` limits which data-call registries a persona can see, run and
# request from. It is enforced server-side.
PERSONAS = {
    "admin": {
        "password": DEMO_PASSWORD,
        "name": "Admin",
        "role": "admin",
        "title": "Data Governance Lead",
        "icon": "shield",
        "accent": "#54755a",
        "tagline": "Governs every registry: retest queue, review SLAs and demand signals.",
        "registries": ALL_REGISTRIES,
        "permissions": ["data_calls", "reports", "governance", "see_all_requests"],
        "kpis": ["needsAttention", "passRate", "oldestPendingDays", "avgReviewDays"],
        "quickActions": [
            {"label": "Open governance", "desc": "Retest queue, SLAs and audit trail", "page": "Governance"},
            {"label": "Browse data calls", "desc": "Search and run calls in both registries", "page": "Data Calls"},
            {"label": "Ask the data", "desc": "Chat with Genie for instant answers", "page": "Ask Data"},
        ],
    },
    "compliance_analyst": {
        "password": DEMO_PASSWORD,
        "name": "Compliance Analyst",
        "role": "analyst",
        "title": "Regulatory Reporting Analyst",
        "icon": "search",
        "accent": "#3b82a6",
        "tagline": "Find, run and request Compliance data calls for regulatory filings.",
        "registries": ["Compliance"],
        "permissions": ["data_calls"],
        "kpis": ["totalCalls", "passRate", "myRequests", "myPending"],
        "quickActions": [
            {"label": "Run a data call", "desc": "Pick a call, set dates, get results", "page": "Data Calls"},
            {"label": "Request a new call", "desc": "Describe what you need; we match it", "page": "Data Calls", "tab": "request"},
        ],
    },
    "finance_analyst": {
        "password": DEMO_PASSWORD,
        "name": "Finance Analyst",
        "role": "finance_analyst",
        "title": "Financial Reporting Analyst",
        "icon": "wallet",
        "accent": "#2f9e8f",
        "tagline": "Find, run and request Financial Reporting data calls for close and reserving.",
        "registries": ["Financial Reporting"],
        "permissions": ["data_calls"],
        "kpis": ["totalCalls", "passRate", "myRequests", "myPending"],
        "quickActions": [
            {"label": "Run a data call", "desc": "Pick a call, set dates, get results", "page": "Data Calls"},
            {"label": "Request a new call", "desc": "Describe what you need; we match it", "page": "Data Calls", "tab": "request"},
        ],
    },
    "it_reviewer": {
        "password": DEMO_PASSWORD,
        "name": "IT Review Team",
        "role": "it_admin",
        "title": "Data Engineering Reviewer",
        "icon": "code",
        "accent": "#7c6fc7",
        "tagline": "Turn approved requests into tested, registered data calls.",
        "registries": ALL_REGISTRIES,
        "permissions": ["data_calls", "it_review", "see_all_requests"],
        "kpis": ["pendingReviews", "approvedCount", "rejectedCount", "totalCalls"],
        "quickActions": [
            {"label": "Open the queue", "desc": "Pending requests waiting on you", "page": "IT Review"},
            {"label": "Browse registries", "desc": "Check for existing coverage", "page": "Data Calls"},
        ],
    },
    "leadership": {
        "password": DEMO_PASSWORD,
        "name": "Executive Leadership",
        "role": "executive",
        "title": "Chief Risk Officer",
        "icon": "chart",
        "accent": "#d99a2b",
        "tagline": "Headline claims and cost analytics, one question away.",
        "registries": ALL_REGISTRIES,
        "permissions": ["reports"],
        "kpis": ["totalCalls", "passRate", "reportCategories"],
        "quickActions": [
            {"label": "Ask the data", "desc": "Plain-English questions, charts back", "page": "Ask Data"},
            {"label": "Enterprise reports", "desc": "Injury, demographic and carrier operations", "page": "Ask Data", "category": "Enterprise / Operational Reports"},
            {"label": "Finance reports", "desc": "Cost, reserves and exposure", "page": "Ask Data", "category": "Finance Reports"},
        ],
    },
}

# Navigation pages and the permission each one needs
PAGE_PERMISSIONS = {
    "Home": None,
    "Data Calls": "data_calls",
    "Governance": "governance",
    "Ask Data": "reports",
    "IT Review": "it_review",
}


# ---------------------------------------------------------------------------
# Data-call test states (from registry table)
# ---------------------------------------------------------------------------
DATA_CALL_STATES = ["All", "TESTED_PASS", "TESTED_FAIL", "NA"]

# ---------------------------------------------------------------------------
# Enterprise Report prompts  (10 per category)
# ---------------------------------------------------------------------------
REPORT_PROMPTS = {
    "Finance Reports": [
        "Claims Cost Summary: show total and average weekly wages by claim status and year",
        "Carrier Liability Exposure: show the open claims count and total wage exposure per carrier",
        "Claims Aging & Reserve Report: show the duration from claim assembly to closure for financial reserve tracking",
        "High-Cost Claims Flagging: flag the top percentile of claims by average weekly wage multiplied by number of dependents",
        "Year-over-Year Cost Trend: show annual claim volume and total wage liability over time",
        "Dependent Liability Analysis: show financial exposure segmented by dependent count brackets",
        "Carrier Type Cost Comparison: show average claim cost and claim volume for each carrier type",
        "District-Level Financial Summary: show total wage exposure and claim counts per district",
        "Claim Settlement Velocity: show the average days between key milestones (PPD scheduled, closed) alongside wage cost",
        "Open Claims Financial Risk: rank all currently open claims by weekly wage and age at injury risk",
    ],
    "Enterprise / Operational Reports": [
        "Injury Classification Distribution: show claim counts by OIICS/WCIO codes and body part",
        "Demographic Risk Profile: show injury frequency by gender, age group and district",
        "Carrier Performance Scorecard: show average resolution time and open/closed ratio per carrier",
        "District Claims Heatmap: show the geographic distribution of claims, injury types and severity by district",
        "Claims Pipeline & Backlog: show the funnel across milestones - assembled, PPD scheduled, closed",
        "Seasonal Accident Trend: show monthly and quarterly accident patterns across years",
        "Age-at-Injury Analysis: show injury type and severity distribution across age bands",
        "Cause-of-Injury Pareto Report: show the top 20% of injury causes driving 80% of claims",
        "Claim Reopening Analysis: show claims with multiple milestone resets that indicate reopened cases",
        "Carrier Market Share Report: show the proportion of total claims handled by each carrier over time",
    ],
}
