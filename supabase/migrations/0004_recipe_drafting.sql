-- DataTales Phase 2.3: automatic recipe drafting by Claude, with a sandbox test run.
--
--   * status:      draft (imported, not yet test-run) | ready (passed the sandbox test: can be
--                  approved) | failed (test failed after one retry) | rejected (by you).
--   * drafted_by:  'claude' (API) or 'manual' (copy-paste / file import).
--   * dataset_id:  the dataset the recipe was drafted and test-run against.
--   * test_report: sandbox result: checks, row count, columns, plain-English summary and the
--                  first 20 cleaned rows. Nothing else is written by a test run.
--   * reject_note: your reason when rejecting.
--
-- Only a recipe that passed its test run can be approved (constraint below), and approved
-- recipes stay immutable (the worker never updates them).
--
-- Run once, in the Supabase dashboard SQL Editor.

begin;

alter table public.recipes
  add column status      text not null default 'draft'
                         check (status in ('draft', 'ready', 'failed', 'rejected')),
  add column drafted_by  text check (drafted_by in ('claude', 'manual')),
  add column dataset_id  uuid references public.datasets (id) on delete set null,
  add column test_report jsonb,
  add column reject_note text;

-- Recipes approved before this migration ran in production, so they count as tested.
update public.recipes set status = 'ready', drafted_by = 'manual' where approved_at is not null;

alter table public.recipes
  add constraint recipes_approved_only_when_ready
  check (approved_at is null or status = 'ready');

create index recipes_status_idx on public.recipes (status, created_at desc);

commit;
