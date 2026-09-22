# Home renovation expense tracker

## Run locally

```bash
pip install -r requirements.txt
streamlit run expense_app.py
```

The app keeps the expense list in the current session. Edit an expense name, total, paid amount, or notes and the row balance plus the summary update automatically.

The electrician amount is initialized to `2,260 MAD`, interpreting the original `- 2260 MAD` entry as a dash/bullet rather than a negative expense. Use the editable field if that was intended to be a credit instead.
