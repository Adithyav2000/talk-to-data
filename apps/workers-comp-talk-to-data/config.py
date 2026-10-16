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

PERSONAS = {
    "compliance_admin": {
        "password": DEMO_PASSWORD,
        "name": "Compliance Admin",
        "role": "admin",
        "title": "Head of Compliance",
        "icon": "shield",
        "accent": "#1f7a5c",
        "tagline": "Oversight of the data-call registry and reports, with visibility into every request.",
        "permissions": ["data_calls", "reports", "see_all_requests"],
        "kpis": ["totalCalls", "passRate", "totalRequests", "pendingReviews"],
        "quickActions": [
            {"label": "Browse data calls", "desc": "Search and run registered calls", "page": "Data Calls"},
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
        "tagline": "Find, run and request the data calls you need for regulatory filings.",
        "permissions": ["data_calls", "reports"],
        "kpis": ["totalCalls", "passRate", "myRequests", "myPending"],
        "quickActions": [
            {"label": "Run a data call", "desc": "Pick a call, set dates, get results", "page": "Data Calls"},
            {"label": "Request a new call", "desc": "Describe what you need; we match it", "page": "Data Calls", "tab": "request"},
            {"label": "Ask the data", "desc": "Explore with natural language", "page": "Ask Data"},
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
        "permissions": ["data_calls", "it_review", "see_all_requests"],
        "kpis": ["pendingReviews", "approvedCount", "rejectedCount", "totalCalls"],
        "quickActions": [
            {"label": "Open the queue", "desc": "Pending requests waiting on you", "page": "IT Review"},
            {"label": "Browse registry", "desc": "Check for existing coverage", "page": "Data Calls"},
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
        "permissions": ["reports"],
        "kpis": ["totalCalls", "passRate", "reportCategories"],
        "quickActions": [
            {"label": "Ask the data", "desc": "Plain-English questions, charts back", "page": "Ask Data"},
            {"label": "Claims overview", "desc": "Counts, trends and denial rates", "page": "Ask Data", "category": "Claims Overview"},
            {"label": "Financial analysis", "desc": "Cost, reserves and liability", "page": "Ask Data", "category": "Financial Analysis"},
        ],
    },
}

# Navigation pages and the permission each one needs
PAGE_PERMISSIONS = {
    "Home": None,
    "Data Calls": "data_calls",
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
    "Claims Overview": [
        "Show total workers compensation claims count by state for the current year",
        "What is the average claim amount by injury type?",
        "Show monthly trend of new claims filed this year",
        "Which states have the highest claim denial rates?",
        "Show top 10 employers by workers comp claim frequency",
        "What is the distribution of claims by worker age group?",
        "Show claim resolution time statistics by state",
        "Compare open vs closed claims across all states",
        "What are the most common injury types reported?",
        "Show quarterly claims volume trend for the last 2 years",
    ],
    "Financial Analysis": [
        "What is the total paid amount across all states this year?",
        "Show average cost per workers compensation claim by state",
        "What are the top 10 most expensive claim types?",
        "Show monthly payment disbursement trends",
        "Compare medical vs indemnity costs by state",
        "What is the reserve adequacy ratio by claim type?",
        "Show outstanding liability by state",
        "What percentage of claims exceed $100,000 in total cost?",
        "Show cost development patterns over claim maturity periods",
        "Compare actual vs expected costs by injury category",
    ],
}
