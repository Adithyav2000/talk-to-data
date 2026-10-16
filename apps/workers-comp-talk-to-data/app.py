"""Workers' Compensation Talk-to-Data  --  Main Streamlit App."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

import config
from genie_client import GenieClient
from data_service import DataService

# ======================================================================
# Page configuration
# ======================================================================
st.set_page_config(
    page_title="Workers' Comp -- Talk to Data",
    page_icon="\U0001f4ca",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================================================================
# Custom CSS  --  Sage Green & White theme
# ======================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ===== Sage Green Palette ===== */
:root {
    --sage:       #5f7161;
    --sage-mid:   #6d8b74;
    --sage-light: #8fac91;
    --sage-pale:  #d0e3cc;
    --cream:      #efead8;
    --olive:      #4a5d4c;
    --forest:     #3d5041;
    --gold:       #c9a84c;
    --coral:      #d9735b;
    --sky:        #6ba3be;
    --bg:         #f7f8f4;
    --card:       #ffffff;
    --border:     #dde5d9;
    --text:       #2d3a2e;
    --text-sec:   #5f6b5f;
}
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text);
}

/* ===== GLOBAL INPUT FIX -- force light mode everywhere ===== */
/* Every input, textarea, select container */
input, textarea, select,
[data-baseweb="input"],
[data-baseweb="input"] input,
[data-baseweb="input"] div,
[data-baseweb="textarea"],
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="select"] [data-baseweb="input"],
[data-baseweb="select"] div[role="combobox"],
[data-baseweb="select"] span,
.stTextInput > div > div,
.stTextArea > div > div,
.stSelectbox > div > div,
.stDateInput > div > div > div {
    background-color: #eef2ea !important;
    color: #2d3a2e !important;
    border-color: #c5d1be !important;
    caret-color: #2d3a2e !important;
    -webkit-text-fill-color: #2d3a2e !important;
}
/* Placeholder text */
input::placeholder, textarea::placeholder {
    color: #8a9a8c !important;
    -webkit-text-fill-color: #8a9a8c !important;
    opacity: 1 !important;
}
/* Select dropdown arrow */
[data-baseweb="select"] svg { fill: #5f7161 !important; }
/* Dropdown menu */
[data-baseweb="popover"], [data-baseweb="menu"],
[data-baseweb="popover"] ul, [data-baseweb="menu"] ul {
    background: #ffffff !important;
    border: 1px solid #c5d1be !important;
}
[data-baseweb="popover"] li,
[data-baseweb="menu"] li {
    background: #ffffff !important;
    color: #2d3a2e !important;
}
[data-baseweb="popover"] li:hover,
[data-baseweb="menu"] li:hover,
[data-baseweb="popover"] li[aria-selected="true"],
[data-baseweb="menu"] li[aria-selected="true"] {
    background: #d0e3cc !important;
}
/* Labels */
label, .stSelectbox label, .stTextInput label, .stTextArea label,
.stDateInput label, .stRadio label, .stCheckbox label {
    color: var(--text) !important;
    font-weight: 500 !important;
}
/* Date input */
[data-baseweb="input"][aria-label],
.stDateInput input { background-color: #eef2ea !important; }
/* Password eye-toggle button */
.stTextInput button,
[data-baseweb="input"] button {
    background: #eef2ea !important;
    color: #5f7161 !important;
    border: none !important;
}
.stTextInput button svg,
[data-baseweb="input"] button svg {
    fill: #5f7161 !important;
}

/* ===== MAIN-AREA BUTTONS -- sage green (excludes sidebar) ===== */
[data-testid="stAppViewContainer"] .stButton button,
[data-testid="stAppViewContainer"] .stFormSubmitButton button,
[data-testid="stAppViewContainer"] button[kind="primary"],
[data-testid="stAppViewContainer"] button[kind="secondary"],
[data-testid="stAppViewContainer"] button[type="submit"],
[data-testid="stAppViewContainer"] .stDownloadButton button {
    background: linear-gradient(135deg, #5f7161, #6d8b74) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(95,113,97,.25) !important;
    transition: all .15s !important;
    -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stAppViewContainer"] .stButton button:hover,
[data-testid="stAppViewContainer"] .stFormSubmitButton button:hover {
    box-shadow: 0 4px 14px rgba(95,113,97,.35) !important;
    transform: translateY(-1px);
}

/* ===== Sidebar  --  sage green ===== */
[data-testid="stSidebar"] {
    background: linear-gradient(175deg, var(--sage) 0%, var(--forest) 100%) !important;
}
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] p { color: #f0f4ec !important; }
[data-testid="stSidebar"] .stRadio label {
    font-weight: 500; font-size: .9rem;
    padding: .35rem .6rem; border-radius: 6px; transition: background .15s;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,.12); }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.15) !important; }
/* Sidebar buttons are styled MUI-flat in the sidebar section below */

/* ===== Metric cards ===== */
.metric-card {
    background: var(--card);
    border-radius: 12px;
    padding: 1.4rem 1rem;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    border-top: 3px solid var(--sage-mid);
    transition: transform .15s, box-shadow .15s;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.08); }
.metric-card h2 { margin: 0; color: var(--forest); font-size: 2.2rem; font-weight: 700; }
.metric-card p  { margin: 6px 0 0; color: var(--text-sec); font-size: .78rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }

.metric-card.card-teal    { border-top-color: var(--sage-mid); }
.metric-card.card-emerald { border-top-color: var(--sage-light); }
.metric-card.card-amber   { border-top-color: var(--gold); }
.metric-card.card-rose    { border-top-color: var(--coral); }

/* ===== Status badges ===== */
.badge {
    display: inline-block; padding: 4px 14px; border-radius: 20px;
    font-size: .73rem; font-weight: 600; letter-spacing: .03em;
}
.badge-pass     { background: #d0e3cc; color: #2d5030; }
.badge-fail     { background: #fde2db; color: #8b3426; }
.badge-na       { background: #e8e5d8; color: #5f5b4a; }
.badge-pending  { background: #fef3c7; color: #7c5e10; }
.badge-approved { background: #d0e3cc; color: #2d5030; }
.badge-rejected { background: #fde2db; color: #8b3426; }

/* ===== Data-call cards ===== */
.dc-card {
    background: var(--card);
    border-radius: 10px;
    padding: 1rem 1.3rem;
    margin-bottom: .7rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
    border-left: 4px solid var(--sage-mid);
    transition: box-shadow .15s;
}
.dc-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,.08); }
.dc-card .dc-title { font-weight: 600; font-size: .95rem; color: var(--forest); }
.dc-card .dc-desc  { color: var(--text-sec); font-size: .82rem; margin: .35rem 0 .2rem; line-height: 1.45; }
.dc-card .dc-file  { font-size: .73rem; color: #8a9a8c; font-family: 'SF Mono', Consolas, monospace; }

/* ===== Chat bubbles ===== */
.chat-user {
    background: #eef4eb; border-radius: 10px; padding: .8rem 1rem;
    margin: .4rem 0; border-left: 3px solid var(--sage-mid);
}
.chat-genie {
    background: #f5f2e8; border-radius: 10px; padding: .8rem 1rem;
    margin: .4rem 0; border-left: 3px solid var(--gold);
}

/* ===== Section header ===== */
.section-header {
    background: linear-gradient(135deg, var(--sage) 0%, var(--sage-mid) 100%);
    color: #ffffff !important;
    font-size: 1.1rem;
    font-weight: 600;
    padding: .75rem 1.2rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    letter-spacing: .01em;
}

/* ===== Forms ===== */
div[data-testid="stForm"] {
    border: 1px solid var(--border); border-radius: 12px; padding: 1.4rem;
    background: var(--card); box-shadow: 0 1px 3px rgba(0,0,0,.04);
}

/* ===== Dataframes ===== */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border); border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}

/* (Buttons styled globally above) */

/* ===== Tabs (override global button green) ===== */
button[data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-sec) !important;
    -webkit-text-fill-color: var(--text-sec) !important;
    box-shadow: none !important;
    font-weight: 600; font-size: .9rem;
    transform: none !important;
}
button[data-baseweb="tab"]:hover {
    background: #eef2ea !important;
    box-shadow: none !important;
    transform: none !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--sage) !important;
    -webkit-text-fill-color: var(--sage) !important;
    border-bottom-color: var(--sage) !important;
    background: transparent !important;
}

/* ===== Radio pills (horizontal) -- not green buttons ===== */
.stRadio > div[role="radiogroup"] button,
.stRadio > div > label {
    background: var(--card) !important;
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    box-shadow: none !important;
    border: 1px solid var(--border) !important;
    transform: none !important;
}
.stRadio > div[role="radiogroup"] button:hover,
.stRadio > div > label:hover {
    background: #eef2ea !important;
    box-shadow: none !important;
    transform: none !important;
}
/* Chart-type selectbox buttons */
button[data-baseweb="tab"]:hover { transform: none !important; }

/* ===== Expanders ===== */
details { border: 1px solid var(--border); border-radius: 10px; }

/* ===== Scrollbar ===== */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--sage-pale); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ======================================================================
# Cached service singletons
# ======================================================================
@st.cache_resource
def _genie():
    return GenieClient(config.GENIE_SPACE_ID)

@st.cache_resource
def _data():
    svc = DataService()
    svc.ensure_tables_exist()
    return svc

# ======================================================================
# Auth helpers
# ======================================================================
def _is_authed() -> bool:
    return st.session_state.get("authenticated", False)

def _login(user: str, pwd: str) -> bool:
    u = config.USERS.get(user)
    if u and u["password"] == pwd:
        st.session_state.update(
            authenticated=True, username=user,
            user_role=u["role"], user_name=u["name"],
        )
        return True
    return False

def _logout():
    for k in ("authenticated", "username", "user_role", "user_name"):
        st.session_state.pop(k, None)

# ======================================================================
# Chart helpers (Plotly)
# ======================================================================
def _auto_chart(df: pd.DataFrame, title: str = ""):
    """Auto-detect the best chart type and render immediately.
    Also shows a manual override selector in an expander."""
    if df.empty:
        return

    num_cols = df.select_dtypes("number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()

    # Try to parse string columns that look like numbers
    for c in list(cat_cols):
        try:
            df[c] = pd.to_numeric(df[c])
            num_cols.append(c)
            cat_cols.remove(c)
        except (ValueError, TypeError):
            pass

    if not num_cols:
        return  # Nothing numeric to chart

    # ---- Auto-detect best chart type ----
    has_time = any(kw in c.lower() for c in cat_cols
                   for kw in ("date", "month", "year", "quarter", "week", "day", "time", "period"))
    n_cats = len(df[cat_cols[0]].unique()) if cat_cols else 0

    if has_time and cat_cols:
        auto_type = "Line"
    elif n_cats <= 6 and cat_cols and num_cols:
        auto_type = "Pie"
    elif cat_cols and num_cols:
        auto_type = "Bar"
    else:
        auto_type = "Bar"

    # Manual override
    chart_types = ["Bar", "Line", "Pie", "Scatter", "Area"]
    default_idx = chart_types.index(auto_type) if auto_type in chart_types else 0
    with st.expander("Change chart type", expanded=False):
        ecol1, ecol2 = st.columns(2)
        with ecol1:
            chart = st.selectbox("Chart type", chart_types,
                                 index=default_idx, key=f"ct_{title}")
        with ecol2:
            color_col = st.selectbox("Color by", [""] + cat_cols, key=f"clr_{title}")
    color = color_col if color_col else None

    try:
        if chart == "Bar" and cat_cols and num_cols:
            fig = px.bar(df, x=cat_cols[0], y=num_cols[0], color=color,
                         title=title, template="plotly_white")
        elif chart == "Line" and num_cols:
            x = cat_cols[0] if cat_cols else df.index
            fig = px.line(df, x=x, y=num_cols[0], color=color,
                          title=title, template="plotly_white",
                          markers=True)
        elif chart == "Pie" and cat_cols and num_cols:
            fig = px.pie(df, names=cat_cols[0], values=num_cols[0],
                         title=title, template="plotly_white",
                         hole=0.35)  # donut style
        elif chart == "Scatter" and len(num_cols) >= 2:
            fig = px.scatter(df, x=num_cols[0], y=num_cols[1], color=color,
                             title=title, template="plotly_white")
        elif chart == "Area" and num_cols:
            x = cat_cols[0] if cat_cols else df.index
            fig = px.area(df, x=x, y=num_cols[0], color=color,
                          title=title, template="plotly_white")
        else:
            fig = px.bar(df, title=title, template="plotly_white")

        fig.update_layout(
            height=420,
            margin=dict(l=40, r=40, t=50, b=40),
            font_family="Inter, sans-serif",
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            colorway=["#6d8b74", "#c9a84c", "#6ba3be", "#d9735b",
                      "#8fac91", "#b08d57", "#7fb5c9", "#5f7161",
                      "#d0e3cc", "#4a5d4c"],
            title_font_color="#3d5041",
            legend_font_color="#5f6b5f",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(f"Could not render chart: {exc}")


def _result_to_df(result: dict) -> pd.DataFrame:
    if "columns" in result and "rows" in result and result["rows"]:
        return pd.DataFrame(result["rows"], columns=result["columns"])
    return pd.DataFrame()


def _ensure_data(res: dict) -> dict:
    """If Genie returned SQL but no tabular rows, execute the SQL directly.
    This is the reliable fallback — Genie's get_message_query_result often
    fails due to permissions, but the SQL itself is valid."""
    has_data = res.get("columns") and res.get("rows")
    if has_data:
        return res
    sql = res.get("sql")
    if not sql:
        return res
    ds = _data()
    result = ds.execute_sql(sql)
    if "columns" in result and result.get("rows"):
        res["columns"] = result["columns"]
        res["rows"] = result["rows"]
    return res

# ======================================================================
# LOGIN PAGE
# ======================================================================
def page_login():
    st.markdown("""
    <div style='text-align:center; padding:2.5rem 2rem 2rem;
                background: linear-gradient(135deg, #5f7161 0%, #6d8b74 50%, #8fac91 100%);
                border-radius: 16px; margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(95,113,97,.25)'>
        <h1 style='color:#ffffff; font-weight:700; letter-spacing:-.02em; margin:0;
                   font-size:2rem'>Workers' Compensation</h1>
        <h3 style='color:#d0e3cc; font-weight:500; margin:.3rem 0 0;
                   font-size:1.1rem'>Talk-to-Data Platform</h3>
        <p style='color:#efead8; font-size:.85rem; margin:.5rem 0 0'>Compliance &middot; Analytics &middot; Enterprise Reports</p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        with st.form("login_form"):
            st.subheader("Sign In")
            user = st.selectbox("Username", list(config.USERS.keys()))
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                if _login(user, pwd):
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

# ======================================================================
# HOME / DASHBOARD
# ======================================================================
def _state_badge(state: str) -> str:
    """Return an HTML badge for a data-call test state."""
    s = (state or "").upper()
    if s == "TESTED_PASS":
        return '<span class="badge badge-pass">TESTED PASS</span>'
    if s == "TESTED_FAIL":
        return '<span class="badge badge-fail">TESTED FAIL</span>'
    return '<span class="badge badge-na">NA</span>'

def page_home():
    st.markdown('<div class="section-header">Dashboard Overview</div>',
                unsafe_allow_html=True)

    ds = _data()
    calls = ds.get_data_calls()
    reqs = ds.get_it_requests()

    total_calls = len(calls.get("rows", []))
    total_reqs = len(reqs.get("rows", []))
    pending = sum(1 for r in reqs.get("rows", []) if "pending" in str(r))

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "Active Data Calls", total_calls, "card-teal"),
        (c2, "IT Requests", total_reqs, "card-emerald"),
        (c3, "Pending Reviews", pending, "card-amber"),
        (c4, "Report Categories", len(config.REPORT_PROMPTS), "card-rose"),
    ]
    for col, label, val, variant in cards:
        col.markdown(
            f'<div class="metric-card {variant}"><h2>{val}</h2><p>{label}</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Recent Data Calls")
        if calls.get("rows"):
            df = _result_to_df(calls).head(5)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No data calls yet.")
    with col_b:
        st.subheader("Recent IT Requests")
        if reqs.get("rows"):
            df = _result_to_df(reqs).head(5)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No IT requests yet.")

# ======================================================================
# DATA CALLS  (Compliance)
# ======================================================================
def page_data_calls():
    st.markdown('<div class="section-header">Data Calls Registry</div>',
                unsafe_allow_html=True)

    ds = _data()

    # Category selector
    cat_names = list(config.DATA_CALL_CATEGORIES.keys())
    selected_cat = st.radio("Category", cat_names, horizontal=True, key="dc_cat")
    active_table = config.DATA_CALL_CATEGORIES[selected_cat]

    tab_browse, tab_request = st.tabs(["Browse Data Calls", "Request New Data Call"])

    # ---- Browse ----
    with tab_browse:
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        with f1:
            search_name = st.text_input("Search by name", key="dc_search",
                                        placeholder="e.g. COVID, aging, audit...")
        with f2:
            state_filter = st.selectbox("Test State", config.DATA_CALL_STATES, key="dc_state")
        with f3:
            from_dt = st.date_input("Query From", value=date(2020, 1, 1), key="dc_from")
        with f4:
            to_dt = st.date_input("Query To", value=date.today(), key="dc_to")

        result = ds.get_data_calls(
            table=active_table,
            state=state_filter,
            name_search=search_name or None,
        )
        if "error" in result:
            st.error(result["error"])
        elif result.get("rows"):
            df = _result_to_df(result)
            # Columns: data_call_id, data_call_name, file_name, description, state
            st.markdown(f'<p style="color:var(--text-muted); font-size:.85rem">{len(df)} data call(s) found</p>',
                        unsafe_allow_html=True)

            # Render a styled card for each data call
            for _, row in df.iterrows():
                badge = _state_badge(str(row.get("state", "NA")))
                st.markdown(f"""
                <div class="dc-card">
                    <div style="display:flex; justify-content:space-between; align-items:center">
                        <span class="dc-title">{row.get('data_call_name', '')}</span>
                        {badge}
                    </div>
                    <p class="dc-desc">{row.get('description', '')}</p>
                    <span class="dc-file">{row.get('file_name', '')}</span>
                </div>
                """, unsafe_allow_html=True)

            # Run selected data call
            st.markdown("---")
            st.subheader("Execute a Data Call")
            names = df["data_call_name"].tolist() if "data_call_name" in df.columns else []
            if names:
                chosen = st.selectbox("Select data call", names, key="run_dc")
                col_btn, col_info = st.columns([1, 3])
                with col_btn:
                    run_clicked = st.button("Query", key="btn_run_dc",
                                            use_container_width=True)
                if run_clicked:
                    row = df[df["data_call_name"] == chosen].iloc[0]
                    desc = str(row.get("description", chosen))
                    prompt = f"{desc} (from {from_dt} to {to_dt})"
                    with st.spinner("Querying..."):
                        res = _genie().ask(prompt)
                        res = _ensure_data(res)
                    if "error" in res:
                        st.error(res["error"])
                    else:
                        rdf = _result_to_df(res)
                        if not rdf.empty:
                            st.markdown(f'<p style="color:#5f7161; font-weight:600; margin-bottom:.3rem">{len(rdf)} rows returned</p>',
                                        unsafe_allow_html=True)
                            st.dataframe(rdf, use_container_width=True, hide_index=True, height=400)
                            # Excel download
                            import io
                            buf = io.BytesIO()
                            rdf.to_excel(buf, index=False, engine="openpyxl")
                            buf.seek(0)
                            st.download_button(
                                "Download Excel",
                                data=buf,
                                file_name=f"{chosen.replace(' ', '_')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                            )
                        if res.get("sql"):
                            with st.expander("Generated SQL"):
                                st.code(res["sql"], language="sql")
                        if res.get("text"):
                            st.info(res["text"])
        else:
            st.info("No data calls match your filters.")

    # ---- Request New ----
    with tab_request:
        st.markdown("""
        Describe the data you need. The system will **semantically match** your
        request against existing data calls. If it is genuinely new, an IT review
        request is created automatically.
        """)

        with st.form("new_request_form"):
            req_desc = st.text_area(
                "Describe the data call you need",
                placeholder="e.g. I need quarterly claim counts broken down by injury type for 2024...",
                height=120,
            )
            submitted = st.form_submit_button("Submit Request", use_container_width=True)

        if submitted and req_desc:
            with st.spinner("Analyzing request and matching against existing data calls..."):
                out = ds.submit_request(req_desc, st.session_state.get("username", "unknown"))

            if out["is_new"]:
                st.success(
                    "This is a **new** data call request. "
                    "An IT review request has been created. The IT team will use Genie "
                    "to generate the SQL, review it, and approve."
                )
                st.metric("Similarity to nearest existing call",
                          f"{out['similarity_score']:.0%}")
            else:
                st.warning(
                    f"A similar data call already exists: **{out['matched_name']}**  \n"
                    f"Similarity score: **{out['similarity_score']:.0%}**  \n"
                    "A review request was still logged so the IT team can verify."
                )

# ======================================================================
# ENTERPRISE REPORTS  (Leadership)
# ======================================================================
def page_enterprise_reports():
    st.markdown('<div class="section-header">Enterprise Reports -- Leadership Analytics</div>',
                unsafe_allow_html=True)

    # initialise conversation memory
    if "report_conv_id" not in st.session_state:
        st.session_state.report_conv_id = None
    if "report_history" not in st.session_state:
        st.session_state.report_history = []

    # ---- Category + prompt picker ----
    cat = st.selectbox("Report category", list(config.REPORT_PROMPTS.keys()), key="rpt_cat")
    prompts = config.REPORT_PROMPTS[cat]

    st.markdown("**Select a report prompt:**")
    cols = st.columns(2)
    for i, p in enumerate(prompts):
        col = cols[i % 2]
        if col.button(p, key=f"rpt_{i}", use_container_width=True):
            st.session_state.report_active_prompt = p
            st.session_state.report_conv_id = None
            st.session_state.report_history = []

    active = st.session_state.get("report_active_prompt")
    if not active:
        st.info("Select a prompt above to generate a report.")
        return

    st.markdown("---")
    st.subheader(f"\U0001f4ca Report: {active}")

    # ---- First query or cached result ----
    cache_key = f"rpt_result_{active}"
    if cache_key not in st.session_state:
        with st.spinner("Genie is generating your report..."):
            res = _genie().ask(active)
            res = _ensure_data(res)  # execute SQL directly if no rows
        st.session_state[cache_key] = res
        st.session_state.report_conv_id = res.get("conversation_id")
        st.session_state.report_history = [
            {"role": "user", "content": active},
            {"role": "genie", "content": res},
        ]
    else:
        res = st.session_state[cache_key]

    # ---- Render ----
    if "error" in res:
        st.error(res["error"])
    else:
        df = _result_to_df(res)
        if not df.empty:
            tab_chart, tab_data, tab_sql = st.tabs(["\U0001f4c8 Chart", "\U0001f4cb Data", "\U0001f4dd SQL"])
            with tab_chart:
                _auto_chart(df, title=active)
            with tab_data:
                st.dataframe(df, use_container_width=True, hide_index=True, height=400)
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, "report.csv", "text/csv")
            with tab_sql:
                st.code(res.get("sql", "N/A"), language="sql")
        if res.get("text"):
            st.info(res["text"])

    # ---- Follow-up chat ----
    st.markdown("---")
    st.subheader("\U0001f4ac Ask follow-up questions")

    for msg in st.session_state.report_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user"><b>You:</b> {msg["content"]}</div>',
                        unsafe_allow_html=True)
        else:
            content = msg["content"]
            if isinstance(content, dict):
                if content.get("text"):
                    st.markdown(f'<div class="chat-genie"><b>Genie:</b> {content["text"]}</div>',
                                unsafe_allow_html=True)
                elif content.get("columns"):
                    st.markdown('<div class="chat-genie"><b>Genie:</b> (see table above)</div>',
                                unsafe_allow_html=True)

    followup = st.chat_input("Ask a follow-up question about this report...")
    if followup:
        st.session_state.report_history.append({"role": "user", "content": followup})
        with st.spinner("Genie is thinking..."):
            fu_res = _genie().ask(
                followup,
                conversation_id=st.session_state.report_conv_id,
            )
            fu_res = _ensure_data(fu_res)
        st.session_state.report_conv_id = fu_res.get("conversation_id",
                                                      st.session_state.report_conv_id)
        st.session_state.report_history.append({"role": "genie", "content": fu_res})

        if "error" in fu_res:
            st.error(fu_res["error"])
        else:
            fu_df = _result_to_df(fu_res)
            if not fu_df.empty:
                st.dataframe(fu_df, use_container_width=True, hide_index=True)
                _auto_chart(fu_df, title=followup)
            if fu_res.get("sql"):
                with st.expander("SQL"):
                    st.code(fu_res["sql"], language="sql")
            if fu_res.get("text"):
                st.info(fu_res["text"])

# ======================================================================
# IT REVIEW  (IT Admin only)
# ======================================================================
def page_it_review():
    st.markdown('<div class="section-header">IT Review Queue</div>',
                unsafe_allow_html=True)

    ds = _data()
    status_filter = st.selectbox("Filter by status", ["All", "pending", "approved", "rejected"],
                                  key="it_filter")
    reqs = ds.get_it_requests(status_filter)

    if "error" in reqs:
        st.error(reqs["error"])
        return
    if not reqs.get("rows"):
        st.info("No requests to review.")
        return

    df = _result_to_df(reqs)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Pending items get review controls
    pending_rows = [r for r in reqs["rows"] if "pending" in str(r).lower()]
    if not pending_rows:
        return

    st.markdown("---")
    st.subheader("Review a pending request")

    req_ids = [str(r[0]) for r in pending_rows]
    chosen_id = st.selectbox("Request ID", req_ids, key="rev_id")
    chosen_row = next(r for r in pending_rows if str(r[0]) == chosen_id)
    req_desc = chosen_row[1] if len(chosen_row) > 1 else ""

    st.write(f"**Description:** {req_desc}")

    # Generate SQL with Genie
    if st.button("\U0001f916 Generate SQL with Genie", key="gen_sql"):
        with st.spinner("Genie is generating SQL..."):
            res = _genie().ask(req_desc)
        if res.get("sql"):
            st.session_state["generated_sql"] = res["sql"]
            st.code(res["sql"], language="sql")
            rdf = _result_to_df(res)
            if not rdf.empty:
                st.dataframe(rdf, use_container_width=True, hide_index=True)
        elif res.get("text"):
            st.info(res["text"])
        elif res.get("error"):
            st.error(res["error"])

    # Approve / Reject
    c_a, c_r = st.columns(2)
    with c_a:
        with st.form("approve_form"):
            st.markdown("**Approve & Create Data Call**")
            dc_name = st.text_input("Data call name", key="appr_name")
            dc_state = st.selectbox("State", config.DATA_CALL_STATES[1:], key="appr_state")
            dc_sql = st.text_area("SQL query",
                                  value=st.session_state.get("generated_sql", ""),
                                  height=120, key="appr_sql")
            if st.form_submit_button("\u2705 Approve", use_container_width=True):
                if dc_name and dc_sql:
                    ds.approve_request(
                        int(chosen_id),
                        st.session_state.get("username", "it"),
                        dc_sql, dc_name, req_desc, dc_state,
                    )
                    st.success("Request approved and data call created!")
                    st.rerun()
                else:
                    st.warning("Name and SQL are required.")

    with c_r:
        with st.form("reject_form"):
            st.markdown("**Reject Request**")
            notes = st.text_area("Rejection notes", height=120, key="rej_notes")
            if st.form_submit_button("\u274c Reject", use_container_width=True):
                ds.reject_request(
                    int(chosen_id),
                    st.session_state.get("username", "it"),
                    notes,
                )
                st.warning("Request rejected.")
                st.rerun()

# ======================================================================
# SIDEBAR + ROUTING
# ======================================================================
def main():
    if not _is_authed():
        page_login()
        return

    # Sidebar
    with st.sidebar:
        # -- MUI-style sidebar CSS --
        st.markdown("""
        <style>
        /* ===== Kill all default sidebar button styling ===== */
        [data-testid="stSidebar"] .stButton {
            margin: 0 !important; padding: 0 !important;
        }
        [data-testid="stSidebar"] .stButton button {
            background: none !important;
            border: none !important;
            border-radius: 6px !important;
            box-shadow: none !important;
            color: rgba(240,244,236,.7) !important;
            -webkit-text-fill-color: rgba(240,244,236,.7) !important;
            font-size: .87rem !important;
            font-weight: 400 !important;
            text-align: left !important;
            padding: .5rem .85rem !important;
            margin: 0 .4rem !important;
            width: calc(100% - .8rem) !important;
            transition: background .12s, color .12s !important;
            transform: none !important;
            line-height: 1.4 !important;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background: rgba(255,255,255,.08) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            box-shadow: none !important;
            transform: none !important;
        }
        [data-testid="stSidebar"] .stButton button:active,
        [data-testid="stSidebar"] .stButton button:focus {
            box-shadow: none !important;
            outline: none !important;
        }
        /* Reduce vertical gap between Streamlit elements in sidebar */
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            gap: 0 !important;
        }
        [data-testid="stSidebar"] .block-container { padding-top: 0 !important; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .15rem !important; }
        </style>
        """, unsafe_allow_html=True)

        # Brand header
        st.markdown("""
        <div style="text-align:center; padding:1.6rem .8rem 1.1rem;
                    border-bottom:1px solid rgba(255,255,255,.1); margin-bottom:.5rem">
            <div style="font-size:1.2rem; font-weight:700; color:#fff; letter-spacing:-.01em">
                Workers' Comp</div>
            <div style="font-size:.72rem; color:rgba(208,227,204,.7); margin-top:.15rem;
                        letter-spacing:.03em">TALK-TO-DATA PLATFORM</div>
        </div>
        """, unsafe_allow_html=True)

        # User card
        uname = st.session_state.user_name
        urole = st.session_state.user_role
        initials = "".join(w[0] for w in uname.split()[:2]).upper()
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:.55rem;
                    padding:.55rem .85rem; margin:0 .4rem .3rem; border-radius:6px;
                    background:rgba(255,255,255,.06)">
            <div style="width:32px; height:32px; border-radius:50%; flex-shrink:0;
                        background:linear-gradient(135deg,#8fac91,#d0e3cc);
                        display:flex; align-items:center; justify-content:center;
                        font-weight:700; font-size:.72rem; color:#3d5041">{initials}</div>
            <div>
                <div style="color:#f0f4ec; font-weight:600; font-size:.82rem; line-height:1.2">{uname}</div>
                <div style="color:rgba(168,196,170,.8); font-size:.62rem; text-transform:uppercase;
                            letter-spacing:.05em; margin-top:1px">{urole}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Section label
        st.markdown("""
        <div style="color:rgba(143,172,145,.6); font-size:.6rem; font-weight:600;
                    text-transform:uppercase; letter-spacing:.1em;
                    padding:.7rem .85rem .25rem .85rem; margin-left:.4rem">Menu</div>
        """, unsafe_allow_html=True)

        # Build page list based on role
        role = st.session_state.user_role
        nav_items = [("Home", "\U0001f3e0")]
        if role in ("admin", "analyst"):
            nav_items.append(("Data Calls", "\U0001f4cb"))
        if role in ("admin", "executive"):
            nav_items.append(("Enterprise Reports", "\U0001f4ca"))
        if role in ("admin", "it_admin"):
            nav_items.append(("IT Review", "\u2699\ufe0f"))

        if "active_page" not in st.session_state:
            st.session_state.active_page = "Home"

        # Inject per-button active highlight via CSS (targets by key)
        active_key = f"nav_{st.session_state.active_page}"
        st.markdown(f"""
        <style>
        [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"][key="{active_key}"],
        [data-testid="stSidebar"] div.stButton:has(button) ~ style + div button {{
            /* fallback */
        }}
        </style>
        """, unsafe_allow_html=True)

        # Render nav buttons
        for label, icon in nav_items:
            is_active = st.session_state.active_page == label
            # Inject active style right before the button
            if is_active:
                st.markdown("""
                <style>
                [data-testid="stSidebar"] .stButton + .stButton button,
                .sidebar-active-next button {
                    /* placeholder */
                }
                </style>
                """, unsafe_allow_html=True)
            if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
                st.session_state.active_page = label
                st.rerun()
            # Re-apply active styling using JS injection
            if is_active:
                st.markdown(f"""
                <script>
                (function() {{
                    const btns = window.parent.document.querySelectorAll(
                        '[data-testid="stSidebar"] button');
                    btns.forEach(b => {{
                        if (b.textContent.includes('{label}')) {{
                            b.style.background = 'rgba(255,255,255,.12)';
                            b.style.color = '#ffffff';
                            b.style.webkitTextFillColor = '#ffffff';
                            b.style.fontWeight = '600';
                            b.style.borderLeft = '3px solid #d0e3cc';
                        }}
                    }});
                }})();
                </script>
                """, unsafe_allow_html=True)

        # Divider + logout
        st.markdown("""
        <div style="border-top:1px solid rgba(255,255,255,.08);
                    margin:1rem .85rem .4rem"></div>
        """, unsafe_allow_html=True)
        if st.button("Logout", key="nav_logout", use_container_width=True):
            _logout()
            st.rerun()

    # Route
    page = st.session_state.active_page
    if page == "Home":
        page_home()
    elif page == "Data Calls":
        page_data_calls()
    elif page == "Enterprise Reports":
        page_enterprise_reports()
    elif page == "IT Review":
        page_it_review()


if __name__ == "__main__":
    main()
