-- DataTales Phase 2: Claude API usage log (budget guard + spend reporting)
--
-- One row per API call (or blocked attempt). The budget guard sums this month's
-- estimated_cost, including 'reserved' rows for calls in flight, before every call.
-- Same lock-down as 0001: RLS on, no policies, service role only.
--
-- Run once, in the Supabase dashboard SQL Editor.

begin;

create table public.llm_calls (
  id                 uuid primary key default gen_random_uuid(),
  task               text not null check (task in ('story', 'recipe', 'discovery', 'check')),
  model              text not null,
  input_tokens       integer not null default 0 check (input_tokens >= 0),
  output_tokens      integer not null default 0 check (output_tokens >= 0),
  cached_tokens      integer not null default 0 check (cached_tokens >= 0),      -- cache reads
  cache_write_tokens integer not null default 0 check (cache_write_tokens >= 0), -- cache writes
  estimated_cost     numeric(12, 6) not null default 0 check (estimated_cost >= 0), -- GBP
  status             text not null
                     check (status in ('reserved', 'ok', 'error', 'invalid_output', 'budget_blocked')),
  related_id         uuid,
  error              text,
  created_at         timestamptz not null default now()
);

create index llm_calls_created_idx on public.llm_calls (created_at desc);
create index llm_calls_related_idx on public.llm_calls (related_id);

alter table public.llm_calls enable row level security;
revoke all on public.llm_calls from anon, authenticated;
grant all on public.llm_calls to service_role;

commit;
