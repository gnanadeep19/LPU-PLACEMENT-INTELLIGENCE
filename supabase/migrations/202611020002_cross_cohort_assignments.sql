-- Individual assignments extend, rather than replace, existing cohort access.
-- Apply only after reviewing and importing any legacy SQLite assignments.
begin;
create table public.mentor_assignments (
  student_id uuid primary key references public.app_users(id) on delete restrict,
  mentor_id uuid not null references public.app_users(id) on delete restrict,
  assigned_by uuid not null references public.app_users(id) on delete restrict,
  updated_at timestamptz not null default now()
);
create index mentor_assignments_mentor_idx on public.mentor_assignments(mentor_id);
alter table public.mentor_assignments enable row level security;
revoke all on public.mentor_assignments from public, anon, authenticated;

create function public.mentor_assignment_admin_list() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare actor public.app_users%rowtype; result jsonb;
begin
  select * into actor from public.app_users where id=(select auth.uid()) and is_active and role='admin';
  if not found then raise exception 'Not authorized' using errcode='42501'; end if;
  select jsonb_build_object(
    'assignments', coalesce((select jsonb_agg(jsonb_build_object('student_id', s.legacy_id, 'mentor_id', m.legacy_id,
      'display_name', m.display_name, 'valid', s.is_active and s.role='student' and m.is_active and m.role='mentor'))
      from public.mentor_assignments a join public.app_users s on s.id=a.student_id
      join public.app_users m on m.id=a.mentor_id where s.legacy_id is not null and m.legacy_id is not null), '[]'::jsonb),
    'mapped_mentors', coalesce((select jsonb_agg(jsonb_build_object('id',legacy_id,'username',username,'cohort',cohort)) from public.app_users where role='mentor' and is_active and legacy_id is not null), '[]'::jsonb),
    'mapped_students', coalesce((select jsonb_agg(jsonb_build_object('id',legacy_id,'username',username,'cohort',cohort)) from public.app_users where role='student' and is_active and legacy_id is not null), '[]'::jsonb)
  ) into result;
  insert into public.staff_audit(actor_id,action) values(actor.id,'view_mentor_assignments');
  return result;
end $$;

create function public.mentor_assignment_set(p_student_id bigint, p_mentor_id bigint, p_student_username text,
  p_student_cohort text, p_mentor_username text, p_mentor_cohort text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare actor public.app_users%rowtype; student public.app_users%rowtype; mentor public.app_users%rowtype;
begin
  select * into actor from public.app_users where id=(select auth.uid()) and is_active and role='admin';
  if not found then raise exception 'Not authorized' using errcode='42501'; end if;
  select * into student from public.app_users where legacy_id=p_student_id and is_active and role='student'
    and username=p_student_username and cohort is not distinct from p_student_cohort;
  if not found then raise exception 'Student not available' using errcode='22023'; end if;
  if p_mentor_id is null then
    delete from public.mentor_assignments where student_id=student.id;
  else
    select * into mentor from public.app_users where legacy_id=p_mentor_id and is_active and role='mentor'
      and username=p_mentor_username and cohort is not distinct from p_mentor_cohort;
    if not found then raise exception 'Mentor not available' using errcode='22023'; end if;
    insert into public.mentor_assignments(student_id, mentor_id, assigned_by)
      values(student.id, mentor.id, actor.id) on conflict(student_id) do update
      set mentor_id=excluded.mentor_id, assigned_by=excluded.assigned_by, updated_at=now();
  end if;
  insert into public.staff_audit(actor_id,action,subject_id) values(actor.id,'update_mentor_assignment',student.id);
  return jsonb_build_object('student_id',p_student_id,'mentor_id',p_mentor_id);
end $$;

create function public.mentor_assignment_mine() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare actor public.app_users%rowtype; result jsonb;
begin
  select * into actor from public.app_users where id=(select auth.uid()) and is_active and role='mentor';
  if not found then raise exception 'Not authorized' using errcode='42501'; end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',s.legacy_id,'username',s.username,'cohort',s.cohort)), '[]'::jsonb) into result from public.mentor_assignments a
    join public.app_users s on s.id=a.student_id where a.mentor_id=actor.id and s.is_active and s.role='student' and s.legacy_id is not null;
  return jsonb_build_object('students',result);
end $$;

create or replace function lpu_private.coaching_target(p_student_id bigint) returns uuid
language plpgsql security definer set search_path = '' as $$
declare actor public.app_users%rowtype; student public.app_users%rowtype;
begin
  select * into actor from public.app_users where id=(select auth.uid()) and is_active and legacy_id is not null;
  if not found then raise exception 'Not authorized' using errcode='42501'; end if;
  select * into student from public.app_users where legacy_id=p_student_id and role='student' and is_active;
  if not found then raise exception 'Student unavailable' using errcode='42501'; end if;
  if actor.role='student' and actor.id<>student.id then raise exception 'Not authorized' using errcode='42501';
  elsif actor.role='mentor' and (actor.cohort is null or actor.cohort is distinct from student.cohort)
    and not exists (select 1 from public.mentor_assignments a where a.student_id=student.id and a.mentor_id=actor.id)
    then raise exception 'Not authorized' using errcode='42501';
  elsif actor.role not in ('student','mentor','admin','placement_officer') then raise exception 'Not authorized' using errcode='42501'; end if;
  return student.id;
end $$;
revoke all on function lpu_private.coaching_target(bigint) from public, anon, authenticated;

create or replace function public.notify_coaching_change() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if tg_op='INSERT' and new.visibility='student' and new.kind in ('goal','check_in') and new.author_id<>new.student_id
     and exists(select 1 from public.app_users u where u.id=new.student_id and u.is_active) then
    insert into public.notifications(recipient_id,kind,title,message,event_key)
      values(new.student_id,'coaching_update',new.title,coalesce(nullif(btrim(new.detail),''),'No description provided.'),'coaching-created:' || new.id::text)
      on conflict(recipient_id,event_key) do nothing;
  elsif tg_op='UPDATE' and old.status is distinct from new.status and new.status='completed' and new.kind='goal'
     and new.visibility='student' and new.author_id<>new.student_id and exists(
       select 1 from public.app_users author join public.app_users student on student.id=new.student_id
       where author.id=new.author_id and author.is_active and student.is_active and
         (author.role in ('admin','placement_officer') or (author.role='mentor' and
           (author.cohort=student.cohort or exists(select 1 from public.mentor_assignments a where a.student_id=student.id and a.mentor_id=author.id))))) then
    insert into public.notifications(recipient_id,kind,title,message,event_key)
      values(new.author_id,'goal_completed','Goal completed','A student goal you created was marked complete. Review the timeline.','goal-completed:' || new.id::text)
      on conflict(recipient_id,event_key) do nothing;
  end if;
  return new;
end $$;
revoke all on function public.mentor_assignment_admin_list(), public.mentor_assignment_set(bigint,bigint,text,text,text,text), public.mentor_assignment_mine() from public, anon, authenticated;
grant execute on function public.mentor_assignment_admin_list(), public.mentor_assignment_set(bigint,bigint,text,text,text,text), public.mentor_assignment_mine() to authenticated;
commit;
