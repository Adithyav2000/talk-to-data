import os

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
# Role-based users (replace with SSO / Databricks OAuth in production)
# ---------------------------------------------------------------------------
USERS = {
    "compliance_admin": {"password": "admin", "role": "admin", "name": "Compliance Admin"},
    "compliance_analyst": {"password": "admin", "role": "analyst", "name": "Compliance Analyst"},
    "it_reviewer": {"password": "admin", "role": "it_admin", "name": "IT Review Team"},
    "leadership": {"password": "admin", "role": "executive", "name": "Executive Leadership"},
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
