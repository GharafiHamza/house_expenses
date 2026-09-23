# Home renovation expense tracker

## Supabase setup

1. In Supabase SQL Editor, run [`supabase/schema.sql`](supabase/schema.sql).
2. In Streamlit Cloud, add `SUPABASE_URL` and `SUPABASE_KEY` under App settings → Secrets. Use the publishable key, never a service-role key.
3. Open the app, create an account, and sign in.

Each expense belongs to its authenticated Supabase user. Row Level Security prevents users from reading or changing another user's expenses.

## Run locally

```bash
pip install -r requirements.txt
streamlit run expense_app.py
```
