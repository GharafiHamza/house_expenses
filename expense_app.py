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

with st.sidebar:
    st.header("Expense tracker")
    st.caption(st.session_state.user.get("email", "Signed-in user"))
    st.button("Add expense", use_container_width=True, on_click=add_expense)
    if st.button("Sign out", use_container_width=True):
        for key in ("access_token", "refresh_token", "user", "expenses", "saved_ids"):
            st.session_state.pop(key, None)
        st.rerun()
    st.divider()
    if st.button("Reset to original figures", use_container_width=True):
        st.session_state.expenses = [{"id": None, **row} for row in DEFAULT_EXPENSES]
        save_expenses()
        st.rerun()

st.caption("Edit any amount below — remaining balances and totals update automatically.")
st.subheader("Expenses")
header = st.columns([2.3, 1.6, 1.6, 1.8, 2.3, 0.6])
for column, label in zip(header, ["Expense", "Total", "Paid", "Remaining", "Notes", ""]):
    column.markdown(f"**{label}**")

for index, row in enumerate(st.session_state.expenses):
    cols = st.columns([2.3, 1.6, 1.6, 1.8, 2.3, 0.6], vertical_alignment="center")
    row["name"] = cols[0].text_input("Expense name", value=row["name"], key=f"name_{index}", label_visibility="visible")
    row["total"] = cols[1].number_input("Total", min_value=None, value=float(row["total"]), step=100.0, key=f"total_{index}", label_visibility="visible")
    row["paid"] = cols[2].number_input("Paid", min_value=None, value=float(row["paid"]), step=100.0, key=f"paid_{index}", label_visibility="visible")
    cols[3].markdown(f"<div class='remaining'>{mad(float(row['total']) - float(row['paid']))}</div>", unsafe_allow_html=True)
    row["notes"] = cols[4].text_input("Notes", value=row["notes"], key=f"notes_{index}", label_visibility="visible")
    if cols[5].button("Delete", key=f"delete_{index}", help="Delete this expense"):
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
:root {
  --canvas: #f7f6f3;
  --surface: #ffffff;
  --ink: #202124;
  --muted: #777873;
  --line: #e6e5e1;
  --accent: #315c4c;
  --accent-soft: #e8f0eb;
}
.stApp { background: var(--canvas); color: var(--ink); }
.block-container { max-width: 1180px; padding: 3.5rem 2rem 5rem; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #f1f0ec; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding: 2rem 1.25rem; }
h1 { font-size: clamp(2rem, 4vw, 3.4rem) !important; letter-spacing: -0.055em; line-height: 1.02 !important; margin-bottom: .65rem !important; }
h2, h3 { letter-spacing: -0.035em; }
[data-testid="stCaptionContainer"] p { color: var(--muted); }
[data-testid="stHorizontalBlock"] { gap: .8rem; align-items: end; }
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) { align-items: stretch; }
[data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1rem 1.1rem; box-shadow: none; }
[data-testid="stMetricLabel"] { color: var(--muted); font-size: .76rem; text-transform: uppercase; letter-spacing: .08em; }
[data-testid="stMetricValue"] { color: var(--ink); font-size: clamp(1.35rem, 3vw, 2rem); letter-spacing: -.04em; }
[data-testid="stTextInput"] label, [data-testid="stNumberInput"] label { color: var(--muted); font-size: .75rem; font-weight: 600; }
[data-baseweb="input"], [data-baseweb="textarea"] { background: var(--surface); border-color: var(--line); border-radius: 7px; }
[data-baseweb="input"]:focus-within { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.stButton > button { min-height: 2.7rem; border-radius: 7px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); font-weight: 600; transition: background .15s ease, transform .15s ease, border-color .15s ease; }
.stButton > button:hover { border-color: #c9c8c2; background: #f2f1ed; }
.stButton > button:active { transform: scale(.98); }
[data-testid="stSidebar"] .stButton > button:first-child { background: var(--ink); color: white; border-color: var(--ink); }
[data-testid="stTabs"] button { color: var(--muted); }
[data-testid="stTabs"] button[aria-selected="true"] { color: var(--ink); }
.remaining { padding: .68rem .8rem; min-height: 2.7rem; border: 1px solid var(--line); border-radius: 7px; background: var(--accent-soft); color: var(--accent); font-weight: 700; font-variant-numeric: tabular-nums; }
[data-testid="stAlert"] { border-radius: 8px; }
@media (max-width: 760px) {
  .block-container { padding: 1.5rem .9rem 3.5rem; }
  [data-testid="stHorizontalBlock"] { flex-direction: column !important; align-items: stretch !important; gap: .55rem; }
  [data-testid="stHorizontalBlock"] > [data-testid="column"] { width: 100% !important; flex: 1 1 auto !important; }
  [data-testid="stMetric"] { padding: .85rem 1rem; }
  [data-testid="stMetricValue"] { font-size: 1.45rem; }
  [data-testid="stSidebar"] { width: 82vw; }
  h1 { font-size: 2.25rem !important; }
  .remaining { margin-top: -.15rem; }
}
@media (prefers-reduced-motion: reduce) {
  .stButton > button { transition: none; }
}
</style>
""", unsafe_allow_html=True)

