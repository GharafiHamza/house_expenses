import os
import uuid

import requests
import streamlit as st


st.set_page_config(page_title="Home renovation expenses", page_icon="💸", layout="wide")

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
    st.button("＋ Add expense", use_container_width=True, on_click=add_expense)
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
    row["name"] = cols[0].text_input("Expense name", value=row["name"], key=f"name_{index}", label_visibility="collapsed")
    row["total"] = cols[1].number_input("Total", min_value=None, value=float(row["total"]), step=100.0, key=f"total_{index}", label_visibility="collapsed")
    row["paid"] = cols[2].number_input("Paid", min_value=None, value=float(row["paid"]), step=100.0, key=f"paid_{index}", label_visibility="collapsed")
    cols[3].markdown(f"<div class='remaining'>{mad(float(row['total']) - float(row['paid']))}</div>", unsafe_allow_html=True)
    row["notes"] = cols[4].text_input("Notes", value=row["notes"], key=f"notes_{index}", label_visibility="collapsed")
    if cols[5].button("✕", key=f"delete_{index}", help="Delete this expense"):
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
[data-testid="stMetric"] { background: #f5f7fb; border: 1px solid #e4e8f0; padding: 1rem; border-radius: 12px; }
.remaining { padding: .55rem .75rem; background: #f8fafc; border-radius: .35rem; min-height: 2.35rem; }
</style>
""", unsafe_allow_html=True)
