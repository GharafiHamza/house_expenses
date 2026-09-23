import os
import uuid

import requests
import streamlit as st


st.set_page_config(page_title="Home renovation expenses", layout="wide")

DEFAULT_EXPENSES = [
    {"name": "Plasterer", "total": 9200.0, "paid": 9200.0, "notes": ""},
    {"name": "Painter", "total": 6000.0, "paid": 0.0, "notes": ""},
    {"name": "Handyman", "total": 1100.0, "paid": 1100.0, "notes": "800 + 300"},
    {"name": "Plumber", "total": 3700.0, "paid": 3500.0, "notes": ""},
    {"name": "Electrician", "total": 2260.0, "paid": 0.0, "notes": ""},
    {"name": "Carpenter", "total": 10000.0, "paid": 10000.0, "notes": ""},
]


def setting(*names: str) -> str | None:
    for name in names:
        try:
            value = st.secrets.get(name)
        except Exception:
            value = None
        if value:
            return str(value)
        value = os.getenv(name)
        if value:
            return value
    return None


def supabase_url() -> str | None:
    return setting("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")


def supabase_key() -> str | None:
    return setting("SUPABASE_KEY", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")


def auth_headers(access_token: str | None = None) -> dict[str, str]:
    token = access_token or st.session_state.get("access_token") or supabase_key()
    return {"apikey": supabase_key() or "", "Authorization": f"Bearer {token}"}


def api_request(method: str, path: str, access_token: str | None = None, **kwargs):
    return requests.request(
        method,
        f"{supabase_url()}{path}",
        headers={**auth_headers(access_token), **kwargs.pop("headers", {})},
        timeout=10,
        **kwargs,
    )


def sign_up(email: str, password: str) -> tuple[bool, str]:
    response = api_request("POST", "/auth/v1/signup", access_token=supabase_key(), json={"email": email, "password": password})
    if response.ok:
        data = response.json()
        if data.get("access_token"):
            st.session_state.access_token = data["access_token"]
            st.session_state.user = data["user"]
            return True, "Account created and signed in."
        return True, "Account created. Check your email to confirm it, then sign in."
    return False, response.json().get("msg", response.text)


def sign_in(email: str, password: str) -> tuple[bool, str]:
    response = api_request("POST", "/auth/v1/token?grant_type=password", access_token=supabase_key(), json={"email": email, "password": password})
    if response.ok:
        data = response.json()
        st.session_state.access_token = data["access_token"]
        st.session_state.user = data["user"]
        st.session_state.pop("expenses", None)
        return True, "Signed in."
    return False, response.json().get("error_description", response.text)


def load_expenses() -> list[dict]:
    response = api_request("GET", "/rest/v1/expenses", params={"select": "id,name,total,paid,notes,position", "order": "position.asc,id.asc"})
    response.raise_for_status()
    return [
        {"id": row["id"], "name": row["name"], "total": float(row["total"]), "paid": float(row["paid"]), "notes": row.get("notes", "")}
        for row in response.json()
    ]


def save_expenses() -> None:
    user_id = st.session_state.user["id"]
    saved_ids = st.session_state.get("saved_ids", set())
    current_ids = set()
    for row in st.session_state.expenses:
        row["id"] = row.get("id") or str(uuid.uuid4())
        current_ids.add(row["id"])
    for removed_id in saved_ids - current_ids:
        api_request("DELETE", "/rest/v1/expenses", params={"id": f"eq.{removed_id}"}).raise_for_status()
    payload = [
        {"id": row["id"], "user_id": user_id, "name": row["name"], "total": row["total"], "paid": row["paid"], "notes": row["notes"], "position": index}
        for index, row in enumerate(st.session_state.expenses)
    ]
    if payload:
        api_request("POST", "/rest/v1/expenses", params={"on_conflict": "id"}, headers={"Prefer": "resolution=merge-duplicates,return=minimal"}, json=payload).raise_for_status()
    st.session_state.saved_ids = current_ids


def mad(value: float) -> str:
    return f"{value:,.0f} MAD"


def add_expense() -> None:
    st.session_state.expenses.append({"id": None, "name": "New expense", "total": 0.0, "paid": 0.0, "notes": ""})


def delete_expense(index: int) -> None:
    st.session_state.expenses.pop(index)


st.title("Home renovation expenses")

if not supabase_url() or not supabase_key():
    st.error("Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY to Streamlit secrets.")
    st.stop()

if "access_token" not in st.session_state:
    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            ok, message = sign_in(email, password)
            (st.success if ok else st.error)(message)
            if ok:
                st.rerun()
    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirmation = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if password != confirmation:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Use a password with at least 6 characters.")
            else:
                ok, message = sign_up(email, password)
                (st.success if ok else st.error)(message)
                if ok and "access_token" in st.session_state:
                    st.rerun()
    st.stop()

if "expenses" not in st.session_state:
    try:
        st.session_state.expenses = load_expenses()
        st.session_state.saved_ids = {row["id"] for row in st.session_state.expenses}
    except requests.RequestException as error:
        st.error(f"Could not load your expenses from Supabase: {error}")
        st.stop()

topbar = st.columns([4.2, 1.1, 1.1, 1.1], vertical_alignment="center")
topbar[0].markdown("<div class='app-wordmark'>Expenses <span>/ Home renovation</span></div>", unsafe_allow_html=True)
topbar[0].caption(st.session_state.user.get("email", "Signed-in user"))
if topbar[1].button("Add", use_container_width=True, on_click=add_expense):
    st.rerun()
if topbar[2].button("Reset", use_container_width=True):
    st.session_state.expenses = [{"id": None, **row} for row in DEFAULT_EXPENSES]
    save_expenses()
    st.rerun()
if topbar[3].button("Sign out", use_container_width=True):
    for key in ("access_token", "refresh_token", "user", "expenses", "saved_ids"):
        st.session_state.pop(key, None)
    st.rerun()
st.caption("A clear view of what has been spent, what is paid, and what remains.")
st.subheader("Expenses")
st.caption("Edit totals, payments, or notes. Remaining is calculated automatically.")

for index, row in enumerate(st.session_state.expenses):
    with st.container(key=f"expense_row_{index}", border=True):
        cols = st.columns([2.5, 1.5, 1.5, 1.8, 2.2, 0.45], vertical_alignment="bottom")
        row["name"] = cols[0].text_input("Expense", value=row["name"], key=f"name_{index}")
        row["total"] = cols[1].number_input("Total", min_value=None, value=float(row["total"]), step=100.0, key=f"total_{index}")
        row["paid"] = cols[2].number_input("Paid", min_value=None, value=float(row["paid"]), step=100.0, key=f"paid_{index}")
        cols[3].markdown(f"<div class='remaining-label'>Remaining</div><div class='remaining'>{mad(float(row['total']) - float(row['paid']))}</div>", unsafe_allow_html=True)
        row["notes"] = cols[4].text_input("Notes", value=row["notes"], key=f"notes_{index}")
        if cols[5].button("×", key=f"delete_{index}", help="Delete this expense"):
            delete_expense(index)
            save_expenses()
            st.rerun()
total = sum(float(row["total"]) for row in st.session_state.expenses)
paid = sum(float(row["paid"]) for row in st.session_state.expenses)
remaining = total - paid

metric_cols = st.columns(3)
metric_cols[0].metric("Total", mad(total))
metric_cols[1].metric("Paid", mad(paid))
metric_cols[2].metric("Remaining", mad(remaining))

st.subheader("Summary")
summary_cols = st.columns([2.3, 1.6, 1.6, 1.8])
summary_cols[0].markdown("**All expenses**")
summary_cols[1].markdown(f"**{mad(total)}**")
summary_cols[2].markdown(f"**{mad(paid)}**")
summary_cols[3].markdown(f"**{mad(remaining)}**")

try:
    save_expenses()
except requests.RequestException as error:
    st.error(f"Could not save your changes: {error}")

st.markdown("""
<style>
:root { --canvas:#fbfbfa; --surface:#fff; --ink:#1d1d1f; --muted:#86868b; --line:#e7e7e5; --accent:#1d1d1f; --accent-soft:#f2f2f0; }
.stApp { background:var(--canvas); color:var(--ink); }
.block-container { max-width:1040px; padding:2rem 2rem 5rem; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { display:none; }
.app-wordmark { color:var(--ink); font-size:1.15rem; font-weight:700; letter-spacing:-.025em; padding-top:.2rem; }
.app-wordmark span { color:var(--muted); font-weight:500; }
h1 { font-size:clamp(2.8rem,7vw,5.4rem) !important; letter-spacing:-.075em; line-height:.95 !important; margin:4.5rem 0 .65rem !important; }
h2,h3 { letter-spacing:-.04em; }
[data-testid="stCaptionContainer"] p { color:var(--muted); }
.topbar { border-bottom:1px solid var(--line); }
[data-testid="stHorizontalBlock"] { gap:.7rem; }
.topbar + div { margin-top:0; }
.stButton > button { min-height:2.45rem; padding:.2rem .85rem; border-radius:7px; border:1px solid var(--line); background:var(--surface); color:var(--ink); font-size:.82rem; font-weight:600; transition:background .15s ease, transform .15s ease; }
.stButton > button:hover { background:#f1f1ef; border-color:#cfcfcb; }
.stButton > button:active { transform:scale(.98); }
[data-testid="stMetric"] { background:transparent; border:0; border-bottom:1px solid var(--line); border-radius:0; padding:.9rem 0 1.1rem; box-shadow:none; }
[data-testid="stMetricLabel"] { color:var(--muted); font-size:.73rem; text-transform:uppercase; letter-spacing:.09em; }
[data-testid="stMetricValue"] { color:var(--ink); font-size:clamp(1.55rem,3vw,2.25rem); letter-spacing:-.055em; }
[data-testid="stTextInput"] label,[data-testid="stNumberInput"] label { color:var(--muted); font-size:.72rem; font-weight:600; }
[data-baseweb="input"],[data-baseweb="textarea"] { background:var(--surface); border-color:var(--line); border-radius:6px; }
[data-baseweb="input"]:focus-within { border-color:var(--ink); box-shadow:0 0 0 1px var(--ink); }
[class*="st-key-expense_row_"] { margin:0; border:0 !important; border-bottom:1px solid var(--line) !important; border-radius:0 !important; background:transparent; }
[class*="st-key-expense_row_"] > div { padding:1.05rem 0 1rem; }
[class*="st-key-expense_row_"] [data-testid="stHorizontalBlock"] { gap:.8rem; align-items:end; }
[class*="st-key-expense_row_"] .stButton > button { min-width:2.3rem; width:2.3rem; padding:0; border:0; background:transparent; color:#a13d38; font-size:1.45rem; line-height:1; }
[class*="st-key-expense_row_"] .stButton > button:hover { background:#fceceb; border:0; }
.remaining-label { color:var(--muted); font-size:.72rem; font-weight:600; margin:0 0 .42rem; }
.remaining { padding:.62rem .75rem; min-height:2.45rem; border:1px solid var(--line); border-radius:6px; background:var(--accent-soft); color:var(--ink); font-weight:700; font-variant-numeric:tabular-nums; }
hr { border-color:var(--line); }
[data-testid="stAlert"] { border-radius:7px; }
@media (max-width:760px) {
  .block-container { padding:1.1rem .9rem 3.5rem; }
  h1 { font-size:3.35rem !important; margin-top:3.5rem !important; }
  .app-wordmark { font-size:1rem; }
  [data-testid="stMetric"] { padding:.75rem 0 1rem; }
  [data-testid="stMetricValue"] { font-size:1.55rem; }
  [class*="st-key-expense_row_"] > div { padding:.95rem 0 .8rem; }
  [class*="st-key-expense_row_"] [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:minmax(0,1fr) minmax(0,1fr) !important; gap:.6rem .7rem; }
  [class*="st-key-expense_row_"] [data-testid="stHorizontalBlock"] > [data-testid="column"] { width:auto !important; flex:none !important; min-width:0 !important; }
  [class*="st-key-expense_row_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child,[class*="st-key-expense_row_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(5) { grid-column:1 / -1; }
  [class*="st-key-expense_row_"] .stButton > button { margin-top:1.65rem; }
}
@media (prefers-reduced-motion:reduce) { .stButton > button { transition:none; } }
</style>
""", unsafe_allow_html=True)



