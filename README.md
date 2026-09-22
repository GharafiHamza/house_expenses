# Home renovation expense tracker

## Run locally

```bash
pip install -r requirements.txt
streamlit run expense_app.py
```

The app saves the expense list to `expenses.json` in the app directory. Edit an expense name, total, paid amount, or notes and the row balance plus the summary update automatically; your changes survive browser refreshes.

The electrician amount is initialized to `2,260 MAD`, interpreting the original `- 2260 MAD` entry as a dash/bullet rather than a negative expense. Use the editable field if that was intended as a credit instead.
