-- Optional reference schema for the Supabase storage backend.
-- The Python app creates these tables automatically when STORAGE_BACKEND=supabase.

create schema if not exists app_private;

create table if not exists app_private.ai_script_tasks (
  id text primary key,
  task_name text,
  business_goal text,
  platform text,
  content_type text,
  target_user text,
  script_count text,
  owner text,
  reviewer text,
  status text,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists app_private.ai_script_products (
  id text primary key,
  task_id text,
  product_name text,
  platform text,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists app_private.ai_script_product_decompositions (
  id text primary key,
  task_id text,
  product_id text,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists app_private.ai_script_topics (
  id text primary key,
  task_id text,
  product_id text,
  decomposition_id text,
  title text,
  angle text,
  difficulty text,
  selected boolean default false,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists app_private.ai_script_scripts (
  id text primary key,
  task_id text,
  topic_id text,
  product_id text,
  title text,
  product_name text,
  platform text,
  generated_at timestamptz,
  saved_at timestamptz,
  exported_at timestamptz,
  status text,
  review_status text,
  reviewer text,
  reject_reason text,
  version_no integer,
  quality_total_score integer,
  quality_grade text,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists app_private.ai_script_script_versions (
  id text primary key,
  script_id text,
  version_no integer,
  source text,
  review_status text,
  saved_at timestamptz,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists app_private.ai_script_script_feedback (
  id text primary key,
  script_id text,
  effect_tag text,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

alter table app_private.ai_script_tasks enable row level security;
alter table app_private.ai_script_products enable row level security;
alter table app_private.ai_script_product_decompositions enable row level security;
alter table app_private.ai_script_topics enable row level security;
alter table app_private.ai_script_scripts enable row level security;
alter table app_private.ai_script_script_versions enable row level security;
alter table app_private.ai_script_script_feedback enable row level security;

create index if not exists ai_script_tasks_created_at_idx
  on app_private.ai_script_tasks (created_at);
create index if not exists ai_script_products_created_at_idx
  on app_private.ai_script_products (created_at);
create index if not exists ai_script_product_decompositions_created_at_idx
  on app_private.ai_script_product_decompositions (created_at);
create index if not exists ai_script_product_decompositions_task_id_idx
  on app_private.ai_script_product_decompositions (task_id);
create index if not exists ai_script_product_decompositions_product_id_idx
  on app_private.ai_script_product_decompositions (product_id);
create index if not exists ai_script_topics_created_at_idx
  on app_private.ai_script_topics (created_at);
create index if not exists ai_script_topics_task_id_idx
  on app_private.ai_script_topics (task_id);
create index if not exists ai_script_topics_product_id_idx
  on app_private.ai_script_topics (product_id);
create index if not exists ai_script_scripts_created_at_idx
  on app_private.ai_script_scripts (created_at);
create index if not exists ai_script_scripts_task_id_idx
  on app_private.ai_script_scripts (task_id);
create index if not exists ai_script_scripts_product_id_idx
  on app_private.ai_script_scripts (product_id);
create index if not exists ai_script_script_versions_created_at_idx
  on app_private.ai_script_script_versions (created_at);
create index if not exists ai_script_script_versions_script_id_idx
  on app_private.ai_script_script_versions (script_id);
create index if not exists ai_script_script_feedback_created_at_idx
  on app_private.ai_script_script_feedback (created_at);
create index if not exists ai_script_script_feedback_script_id_idx
  on app_private.ai_script_script_feedback (script_id);
