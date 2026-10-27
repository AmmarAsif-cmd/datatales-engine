-- DataTales: monthly Claude budget top-ups (dashboard "Add £5 this month" button).
--
-- The base budget is `monthly_budget_gbp` in worker/config/llm.yaml. Each row here adds
-- `amount_gbp` to the budget for one calendar month (UTC) only; nothing carries over.
-- `step` numbers the top-ups within a month (1, 2, 3...). The unique (month, step) pair
-- means two clicks at the same moment cannot both add the same step, so the per-month cap
-- (`max_topup_gbp_per_month` in llm.yaml, checked by the dashboard) cannot be overshot.
-- Same lock-down as 0001: RLS on, no policies, service role only.
--
-- Run once, in the Supabase dashboard SQL Editor.

begin;

create table public.llm_budget_topups (
  id          uuid primary key default gen_random_uuid(),
  month       date not null check (extract(day from month) = 1),
  step        integer not null check (step between 1 and 20),
  amount_gbp  numeric(8, 2) not null check (amount_gbp > 0 and amount_gbp <= 50),
  added_by    text not null,
  created_at  timestamptz not null default now(),
  unique (month, step)
);

alter table public.llm_budget_topups enable row level security;
revoke all on public.llm_budget_topups from anon, authenticated;
grant all on public.llm_budget_topups to service_role;

commit;
