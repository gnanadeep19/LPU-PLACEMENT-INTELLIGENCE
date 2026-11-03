-- Development migration: scheduled, idempotent reminders for visible goals.
-- Requires the preceding coaching and cross-cohort assignment migrations and
-- the pg_cron extension. Apply and test in the development project first.
begin;
create extension if not exists pg_cron with schema pg_catalog;

create or replace function public.enqueue_goal_reminders() returns integer
language plpgsql security definer set search_path = '' as $$
declare today date := (now() at time zone 'Asia/Kolkata')::date; inserted integer := 0;
begin
  with eligible as (
    select r.*, case when r.due_date < today then 'overdue'
                     when r.due_date = today then 'due today'
                     else 'upcoming' end as phase
    from public.coaching_records r
    join public.app_users s on s.id=r.student_id and s.is_active and s.role='student'
    where r.kind='goal' and r.visibility='student' and r.status in ('open','in_progress')
      and r.due_date is not null and r.due_date <= today + 3
  ), recipients as (
    select e.id, e.student_id as recipient_id, e.title, e.due_date, e.phase from eligible e
    union all
    select e.id, a.id, e.title, e.due_date, e.phase from eligible e
    join public.app_users a on a.id=e.author_id and a.is_active
    join public.app_users s on s.id=e.student_id and s.is_active
    where a.id <> s.id and (a.role in ('admin','placement_officer') or
      (a.role='mentor' and (a.cohort=s.cohort or exists
        (select 1 from public.mentor_assignments ma where ma.student_id=s.id and ma.mentor_id=a.id))))
  ), added as (
    insert into public.notifications(recipient_id,kind,title,message,event_key)
    select recipient_id, 'goal_reminder', 'Goal ' || phase,
      title || ' · Due ' || due_date::text,
      'goal-reminder:' || id::text || ':' || due_date::text || ':' || phase
    from recipients
    on conflict (recipient_id,event_key) do nothing returning 1
  ) select count(*) into inserted from added;
  return inserted;
end $$;
revoke all on function public.enqueue_goal_reminders() from public, anon, authenticated;

-- SQLite resource uploads call this only after saving the file. Each call
-- independently verifies the staff role and student scope at the DB boundary.
create or replace function public.resource_shared_notify(p_student_id bigint, p_resource_id bigint, p_title text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare actor public.app_users%rowtype; student uuid;
begin
  select * into actor from public.app_users where id=(select auth.uid()) and is_active and role in ('mentor','admin','placement_officer');
  if not found then raise exception 'Not authorized' using errcode='42501'; end if;
  if p_resource_id is null or p_resource_id <= 0 or length(btrim(coalesce(p_title,''))) not between 1 and 140 then
    raise exception 'Invalid resource details' using errcode='22023';
  end if;
  student := lpu_private.coaching_target(p_student_id);
  insert into public.notifications(recipient_id,kind,title,message,event_key)
    values(student,'study_resource','New study resource',btrim(p_title),
      'resource-shared:' || p_student_id::text || ':' || p_resource_id::text)
    on conflict(recipient_id,event_key) do nothing;
  insert into public.staff_audit(actor_id,action,subject_id) values(actor.id,'notify_study_resource',student);
  return jsonb_build_object('sent',true);
end $$;
revoke all on function public.resource_shared_notify(bigint,bigint,text) from public, anon, authenticated;
grant execute on function public.resource_shared_notify(bigint,bigint,text) to authenticated;

-- Runs daily at 03:00 UTC (08:30 India time). Replace only this named job so
-- the migration can be reapplied without creating duplicate scheduled runs.
do $$
declare existing_job bigint;
begin
  select jobid into existing_job from cron.job where jobname='lpu-goal-reminders';
  if existing_job is not null then perform cron.unschedule(existing_job); end if;
  perform cron.schedule('lpu-goal-reminders', '0 3 * * *', 'select public.enqueue_goal_reminders()');
end $$;
commit;
