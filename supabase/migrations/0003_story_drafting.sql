-- DataTales Phase 2.2: automatic story drafting by Claude.
--
--   * status 'failed': Claude's draft did not pass verification after one retry. The text and
--     the verify report stay on the story so it can be fixed by hand (or redrafted).
--   * drafted_by:    'claude' (API) or 'manual' (copy-paste); null until narrated.
--   * candidate_key: which candidate this story is about (source, level, place, direction),
--                    so the pipeline does not draft the same story twice.
--   * data_version:  the clean table the story was built from; a new one means new data.
--   * draft_note:    why automatic drafting stopped (e.g. budget reached), shown in the dashboard.
--
-- Run once, in the Supabase dashboard SQL Editor.

begin;

alter table public.stories drop constraint stories_status_check;
alter table public.stories add constraint stories_status_check
  check (status in ('draft', 'approved', 'rejected', 'published', 'failed'));

alter table public.stories
  add column drafted_by    text check (drafted_by in ('claude', 'manual')),
  add column candidate_key text,
  add column data_version  text,
  add column draft_note    text;

create index stories_candidate_key_idx on public.stories (candidate_key);

-- Stories narrated before this migration were pasted by hand.
update public.stories set drafted_by = 'manual' where headline is not null and verify_report is not null;

commit;
