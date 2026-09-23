-- Run this in Supabase SQL Editor before starting the app.
create table if not exists public.expenses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  total numeric not null default 0,
  paid numeric not null default 0,
  notes text not null default '',
  position integer not null default 0,
  created_at timestamptz not null default now()
);

alter table public.expenses enable row level security;

drop policy if exists "expenses_select_own" on public.expenses;
drop policy if exists "expenses_insert_own" on public.expenses;
drop policy if exists "expenses_update_own" on public.expenses;
drop policy if exists "expenses_delete_own" on public.expenses;

create policy "expenses_select_own" on public.expenses for select to authenticated using (auth.uid() = user_id);
create policy "expenses_insert_own" on public.expenses for insert to authenticated with check (auth.uid() = user_id);
create policy "expenses_update_own" on public.expenses for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "expenses_delete_own" on public.expenses for delete to authenticated using (auth.uid() = user_id);
