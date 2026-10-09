-- DataTales Story Engine: initial schema
--
-- Security model:
--   * RLS is enabled on every table, with NO policies. anon and authenticated can read
--     and write nothing. Only the service role (worker + local dashboard) bypasses RLS.
--   * Table privileges are also revoked from anon/authenticated as a second lock.
--   * Storage buckets `raw` and `clean` are private.
--
-- Run once, in the Supabase dashboard SQL Editor (see README "Database setup").

begin;

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- sources: where data comes from
-- ---------------------------------------------------------------------------

create table public.sources (
  id               uuid primary key default gen_random_uuid(),
  slug             text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  name             text not null,
  publisher        text not null,
  url              text not null,
  licence          text,
  refresh_schedule text,
  relatability     smallint not null default 3 check (relatability between 1 and 5),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- datasets: each fetched raw file (stored untouched in the `raw` bucket)
-- ---------------------------------------------------------------------------

create table public.datasets (
  id          uuid primary key default gen_random_uuid(),
  source_id   uuid not null references public.sources (id) on delete restrict,
  raw_path    text not null,
  fetched_at  timestamptz not null default now(),
  checksum    text not null check (checksum ~ '^[0-9a-f]{64}$'),
  profile     jsonb,
  created_at  timestamptz not null default now(),
  unique (source_id, checksum)
);

create index datasets_source_fetched_idx on public.datasets (source_id, fetched_at desc);

-- ---------------------------------------------------------------------------
-- recipes: declarative cleaning recipes (only approved ones run)
-- ---------------------------------------------------------------------------

create table public.recipes (
  id           uuid primary key default gen_random_uuid(),
  source_id    uuid not null references public.sources (id) on delete restrict,
  version      integer not null check (version > 0),
  spec         jsonb not null,
  approved_at  timestamptz,
  approved_by  text,
  created_at   timestamptz not null default now(),
  unique (source_id, version),
  check ((approved_at is null) = (approved_by is null))
);

create index recipes_approved_idx on public.recipes (source_id, version desc)
  where approved_at is not null;

-- ---------------------------------------------------------------------------
-- clean_tables: cleaned Parquet outputs (stored in the `clean` bucket)
-- ---------------------------------------------------------------------------

create table public.clean_tables (
  id             uuid primary key default gen_random_uuid(),
  dataset_id     uuid not null references public.datasets (id) on delete cascade,
  recipe_id      uuid not null references public.recipes (id) on delete restrict,
  parquet_path   text not null,
  row_count      integer not null check (row_count >= 0),
  checks         jsonb not null default '[]'::jsonb,
  checks_passed  boolean not null default false,
  created_at     timestamptz not null default now(),
  unique (dataset_id, recipe_id)
);

create index clean_tables_recipe_idx on public.clean_tables (recipe_id);

-- ---------------------------------------------------------------------------
-- findings: detector results, with the exact numbers used
-- ---------------------------------------------------------------------------

create table public.findings (
  id              uuid primary key default gen_random_uuid(),
  clean_table_id  uuid not null references public.clean_tables (id) on delete cascade,
  detector        text not null,
  title_hint      text,
  numbers         jsonb not null,
  score           numeric not null check (score between 0 and 1),
  created_at      timestamptz not null default now()
);

create index findings_clean_table_score_idx on public.findings (clean_table_id, score desc);

-- ---------------------------------------------------------------------------
-- stories: narrated drafts through to published
-- ---------------------------------------------------------------------------

create table public.stories (
  id             uuid primary key default gen_random_uuid(),
  finding_ids    uuid[] not null check (cardinality(finding_ids) > 0),
  slug           text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  headline       text,
  hook           text,
  summary        text,
  body_md        text,
  video_script   text,
  chart_spec     jsonb,
  chart_data     jsonb,
  numbers        jsonb,
  verify_status  text not null default 'pending'
                 check (verify_status in ('pending', 'passed', 'failed')),
  verify_report  jsonb,
  status         text not null default 'draft'
                 check (status in ('draft', 'approved', 'rejected', 'published')),
  published_at   timestamptz,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  -- A story can only be approved or published once verification has passed.
  constraint stories_verified_before_approval
    check (status not in ('approved', 'published') or verify_status = 'passed'),
  constraint stories_published_at_set
    check ((status = 'published') = (published_at is not null))
);

create index stories_status_idx on public.stories (status, updated_at desc);
create index stories_finding_ids_idx on public.stories using gin (finding_ids);

create trigger stories_set_updated_at
  before update on public.stories
  for each row execute function public.set_updated_at();

create trigger sources_set_updated_at
  before update on public.sources
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- jobs: pipeline runs
-- ---------------------------------------------------------------------------

create table public.jobs (
  id           uuid primary key default gen_random_uuid(),
  type         text not null,
  status       text not null default 'running'
               check (status in ('queued', 'running', 'succeeded', 'failed')),
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  log          text,
  error        text
);

create index jobs_started_idx on public.jobs (started_at desc);

-- ---------------------------------------------------------------------------
-- Lock down: RLS on every table, no policies, no anon/authenticated privileges
-- ---------------------------------------------------------------------------

alter table public.sources      enable row level security;
alter table public.datasets     enable row level security;
alter table public.recipes      enable row level security;
alter table public.clean_tables enable row level security;
alter table public.findings     enable row level security;
alter table public.stories      enable row level security;
alter table public.jobs         enable row level security;

revoke all on
  public.sources, public.datasets, public.recipes, public.clean_tables,
  public.findings, public.stories, public.jobs
from anon, authenticated;

grant all on
  public.sources, public.datasets, public.recipes, public.clean_tables,
  public.findings, public.stories, public.jobs
to service_role;

revoke execute on function public.set_updated_at() from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- Security self-check used by `python -m datatales db-check` (service role only)
-- ---------------------------------------------------------------------------

create or replace function public.dt_security_status()
returns table (
  table_name    text,
  rls_enabled   boolean,
  policy_count  integer,
  anon_select   boolean,
  auth_select   boolean
)
language sql
stable
set search_path = ''
as $$
  select
    c.relname::text,
    c.relrowsecurity,
    (select count(*)::int from pg_catalog.pg_policies p
       where p.schemaname = 'public' and p.tablename = c.relname),
    pg_catalog.has_table_privilege('anon', c.oid, 'SELECT'),
    pg_catalog.has_table_privilege('authenticated', c.oid, 'SELECT')
  from pg_catalog.pg_class c
  join pg_catalog.pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind in ('r', 'p')
  order by c.relname;
$$;

revoke execute on function public.dt_security_status() from public, anon, authenticated;
grant execute on function public.dt_security_status() to service_role;

-- ---------------------------------------------------------------------------
-- Storage: private buckets (50 MB per file = free-tier limit)
-- ---------------------------------------------------------------------------

insert into storage.buckets (id, name, public, file_size_limit)
values
  ('raw',   'raw',   false, 52428800),
  ('clean', 'clean', false, 52428800)
on conflict (id) do update
  set public = false;

commit;
