import json
from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="Home renovation expenses",
    page_icon="💸",
    layout="wide",
)


DEFAULT_EXPENSES = [
    {"name": "Plasterer", "total": 9200.0, "paid": 9200.0, "notes": ""},
    {"name": "Painter", "total": 6000.0, "paid": 0.0, "notes": ""},
    {"name": "Handyman", "total": 1100.0, "paid": 1100.0, "notes": "800 + 300"},
    {"name": "Plumber", "total": 3700.0, "paid": 3500.0, "notes": ""},
    {"name": "Electrician", "total": 2260.0, "paid": 0.0, "notes": ""},
    {"name": "Carpenter", "total": 10000.0, "paid": 10000.0, "notes": ""},
]

DATA_FILE = Path(__file__).with_name("expenses.json")


def mad(value: float) -> str:
    return f"{value:,.0f} MAD"


def load_expenses() -> list[dict]:
    if DATA_FILE.exists():
        try:
            stored = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(stored, list):
                return stored
        except (json.JSONDecodeError, OSError):
            pass
    return [row.copy() for row in DEFAULT_EXPENSES]


def save_expenses() -> None:
    DATA_FILE.write_text(
        json.dumps(st.session_state.expenses, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def ensure_state() -> None:
    if "expenses" not in st.session_state:
        st.session_state.expenses = load_expenses()


def add_expense() -> None:
    st.session_state.expenses.append(
        {"name": "New expense", "total": 0.0, "paid": 0.0, "notes": ""}
    )


def delete_expense(index: int) -> None:
    st.session_state.expenses.pop(index)


ensure_state()

st.title("Home renovation expenses")
st.caption("Edit any amount below — remaining balances and totals update automatically.")

with st.sidebar:
    st.header("Expense tracker")
    st.button("＋ Add expense", use_container_width=True, on_click=add_expense)
    st.divider()
    st.info("Tip: enter amounts as plain numbers. Negative values are supported for credits or refunds.")
    if st.button("Reset to original figures", use_container_width=True):
        st.session_state.expenses = [row.copy() for row in DEFAULT_EXPENSES]
        save_expenses()
        st.rerun()

total = sum(float(row["total"]) for row in st.session_state.expenses)
paid = sum(float(row["paid"]) for row in st.session_state.expenses)
remaining = total - paid

metric_cols = st.columns(3)
metric_cols[0].metric("Total", mad(total))
metric_cols[1].metric("Paid", mad(paid))
metric_cols[2].metric("Remaining", mad(remaining), delta=None)

st.subheader("Expenses")
header = st.columns([2.3, 1.6, 1.6, 1.8, 2.3, 0.6])
for column, label in zip(header, ["Expense", "Total", "Paid", "Remaining", "Notes", ""]):
    column.markdown(f"**{label}**")

for index, row in enumerate(st.session_state.expenses):
    cols = st.columns([2.3, 1.6, 1.6, 1.8, 2.3, 0.6], vertical_alignment="center")
    row["name"] = cols[0].text_input(
        "Expense name", value=row["name"], key=f"name_{index}", label_visibility="collapsed"
    )
    row["total"] = cols[1].number_input(
        "Total", min_value=None, value=float(row["total"]), step=100.0,
        key=f"total_{index}", label_visibility="collapsed"
    )
    row["paid"] = cols[2].number_input(
        "Paid", min_value=None, value=float(row["paid"]), step=100.0,
        key=f"paid_{index}", label_visibility="collapsed"
    )
    current_remaining = float(row["total"]) - float(row["paid"])
    cols[3].markdown(f"<div class='remaining'>{mad(current_remaining)}</div>", unsafe_allow_html=True)
    row["notes"] = cols[4].text_input(
        "Notes", value=row["notes"], key=f"notes_{index}", label_visibility="collapsed"
    )
    if cols[5].button("✕", key=f"delete_{index}", help="Delete this expense"):
        delete_expense(index)
        save_expenses()
        st.rerun()

st.divider()
st.subheader("Summary")
summary_cols = st.columns([2.3, 1.6, 1.6, 1.8])
summary_cols[0].markdown("**All expenses**")
summary_cols[1].markdown(f"**{mad(total)}**")
summary_cols[2].markdown(f"**{mad(paid)}**")
summary_cols[3].markdown(f"**{mad(remaining)}**")

# Streamlit reruns after every widget change. Saving at the end of each run
# makes edits survive browser refreshes and app restarts on the same instance.
save_expenses()

st.markdown(
    """
    <style>
    [data-testid="stMetric"] { background: #f5f7fb; border: 1px solid #e4e8f0; padding: 1rem; border-radius: 12px; }
    .remaining { padding: .55rem .75rem; background: #f8fafc; border-radius: .35rem; min-height: 2.35rem; }
    [data-testid="stDataFrame"] { border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)
