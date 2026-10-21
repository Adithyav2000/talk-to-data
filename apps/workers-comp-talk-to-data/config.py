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

# Fallback workspace folder for SQL files when a registry has none to copy the location from
SQL_ASSET_ROOT = os.getenv("SQL_ASSET_ROOT", "")

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
# Enterprise Report prompts
#
# Each asks for one simple breakdown (one label column, one or two numbers) so
# the answer is a small table and a chart that is easy to explain in a demo.
# ---------------------------------------------------------------------------
REPORT_PROMPTS = {
    "Finance Reports": [
        "Claims per Year: how many claims were filed in each accident year since 2010? One row per year, oldest first.",
        "Open vs. Closed: how many claims are in each current claim status? One row per status, most claims first.",
        "Average Weekly Wage per Year: what is the average weekly wage of injured workers in each accident year since 2010? One row per year.",
        "Top 10 Carriers by Open Claims: which 10 carriers have the most open claims? Show carrier name and open claim count.",
        "Wage by Carrier Type: what is the average weekly wage for each carrier type? One row per carrier type.",
        "Open Claims by District: how many open claims does each district have? One row per district, most first.",
        "Days to Close: on average, how many days does it take to close a claim, for each accident year since 2010? One row per year.",
        "Claims by Dependents: how many claims have 0, 1, 2, 3, or 4 or more dependents? One row per group.",
    ],
    "Enterprise / Operational Reports": [
        "Claims by District: how many claims does each district have? One row per district, most first.",
        "Top 10 Injured Body Parts: which 10 body parts are injured most often? Show body part and claim count.",
        "Top 10 Causes of Injury: what are the 10 most common causes of injury? Show cause and claim count.",
        "Claims by Gender: how many claims are there for each gender? One row per gender.",
        "Claims by Age Group: how many claims are there per age-at-injury group (under 25, 25-34, 35-44, 45-54, 55-64, 65+)?",
        "Accidents by Month: across all years, how many accidents happen in each calendar month? One row per month, January to December.",
        "Top 10 Carriers by Claims: which 10 carriers handle the most claims? Show carrier name and claim count.",
        "Claims Closed per Year: how many claims were closed in each year since 2010? One row per year, oldest first.",
    ],
}
