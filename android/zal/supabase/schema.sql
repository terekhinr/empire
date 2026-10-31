-- Zal / Empire gym sync schema for Supabase
-- Run in SQL Editor of your project.

create table if not exists strength_logs (
  uuid uuid primary key,
  logged_on date not null,
  exercise_key text not null,
  exercise_label text,
  weight_kg double precision not null default 0,
  reps integer not null default 0,
  sets integer not null default 1,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted boolean not null default false
);

create index if not exists strength_logs_updated on strength_logs (updated_at);
create index if not exists strength_logs_day on strength_logs (logged_on);

create table if not exists measurements (
  uuid uuid primary key,
  measured_on date not null,
  weight_kg double precision,
  waist_cm double precision,
  biceps_r_cm double precision,
  biceps_l_cm double precision,
  legs_cm double precision,
  note text,
  source text not null default 'android',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted boolean not null default false
);

create index if not exists measurements_updated on measurements (updated_at);
create index if not exists measurements_day on measurements (measured_on);

-- Personal single-user policies (anon key). Tighten later if shared.
alter table strength_logs enable row level security;
alter table measurements enable row level security;

drop policy if exists zal_logs_all on strength_logs;
create policy zal_logs_all on strength_logs
  for all
  using (true)
  with check (true);

drop policy if exists zal_meas_all on measurements;
create policy zal_meas_all on measurements
  for all
  using (true)
  with check (true);

-- Allow anon role via PostgREST
grant select, insert, update, delete on strength_logs to anon, authenticated;
grant select, insert, update, delete on measurements to anon, authenticated;
