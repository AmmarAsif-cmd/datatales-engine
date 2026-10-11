-- DataTales Phase 2.5: weekly new-dataset step.
--
--   * recipes.detect_spec: for a source added from the backlog, the detector settings Claude
--     drafted with the recipe (which column is the place, the period, the value, how to slice
--     it). It was test-run on the cleaned data; approving the recipe writes it into the
--     source's file (worker/sources.d/<slug>.yaml) so the source joins the weekly pipeline.
--
-- Run once, in the Supabase dashboard SQL Editor.

begin;

alter table public.recipes add column detect_spec jsonb;

commit;
