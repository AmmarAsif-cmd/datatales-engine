-- DataTales Phase 2.4: dataset discovery backlog.
--
-- Weekly discovery adds the best new UK datasets as 'suggested'; you accept or reject them in
-- the dashboard. A rejected (or any existing) source_url is never suggested again. P2.5 takes
-- the highest-scored 'accepted' item each week, adds it as a source and ingests it.
-- Same lock-down as 0001: RLS on, no policies, service role only.
--
-- Run once, in the Supabase dashboard SQL Editor.

begin;

create table public.dataset_backlog (
  id               uuid primary key default gen_random_uuid(),
  title            text not null,
  publisher        text not null,
  source_url       text not null unique,
  catalogue        text not null check (catalogue in ('data_gov_uk', 'ons', 'seed')),
  catalogue_id     text,
  licence          text not null,
  formats          text[] not null default '{}',
  update_frequency text,
  geography_levels text[] not null default '{}',
  has_time_series  boolean,
  score            integer check (score between 0 and 100),
  pitch            text,
  status           text not null default 'suggested'
                   check (status in ('suggested', 'accepted', 'rejected', 'ingested')),
  reject_reason    text,
  error            text,          -- P2.5: why adding it to the pipeline failed
  source_slug      text,          -- P2.5: the source created from it
  last_updated     timestamptz,   -- from the catalogue
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index dataset_backlog_status_idx on public.dataset_backlog (status, score desc);

create trigger dataset_backlog_set_updated_at
  before update on public.dataset_backlog
  for each row execute function public.set_updated_at();

alter table public.dataset_backlog enable row level security;
revoke all on public.dataset_backlog from anon, authenticated;
grant all on public.dataset_backlog to service_role;

commit;
