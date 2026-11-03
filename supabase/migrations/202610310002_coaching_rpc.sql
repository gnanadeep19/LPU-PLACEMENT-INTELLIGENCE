-- Optional transition path. Review and test with synthetic accounts before use.
-- The PostgreSQL account/cohort assignment is authoritative for these RPCs.
-- No authenticated client receives direct table write privileges.
begin;
create schema lpu_private;
revoke all on schema lpu_private from public, anon, authenticated;

create function lpu_private.coaching_target(p_student_id bigint) returns uuid
language plpgsql security definer set search_path = '' as $$
declare
  actor public.app_users%rowtype;
  student public.app_users%rowtype;
begin
  select * into actor from public.app_users where id = (select auth.uid()) and is_active and legacy_id is not null;
  if not found then raise exception 'Not authorized' using errcode = '42501'; end if;
  select * into student from public.app_users where legacy_id = p_student_id and role = 'student' and is_active;
  if not found then raise exception 'Student unavailable' using errcode = '42501'; end if;
  if actor.role = 'student' and actor.id <> student.id then
    raise exception 'Not authorized' using errcode = '42501';
  elsif actor.role = 'mentor' and (actor.cohort is null or actor.cohort is distinct from student.cohort) then
    raise exception 'Not authorized' using errcode = '42501';
  elsif actor.role not in ('student', 'mentor', 'admin', 'placement_officer') then
    raise exception 'Not authorized' using errcode = '42501';
  end if;
  return student.id;
end;
$$;
revoke all on function lpu_private.coaching_target(bigint) from public, anon, authenticated;

create function lpu_private.coaching_json(p_record public.coaching_records) returns jsonb
language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'id', p_record.id, 'student_id', student.legacy_id, 'author_id', author.legacy_id,
    'kind', p_record.kind, 'title', p_record.title, 'detail', p_record.detail,
    'due_date', p_record.due_date, 'status', p_record.status, 'visibility', p_record.visibility,
    'evidence_url', p_record.evidence_url, 'created_at', p_record.created_at, 'updated_at', p_record.updated_at
  ) from public.app_users student, public.app_users author
    where student.id = p_record.student_id and author.id = p_record.author_id;
$$;
revoke all on function lpu_private.coaching_json(public.coaching_records) from public, anon, authenticated;

create function public.coaching_list(p_student_id bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  target uuid := lpu_private.coaching_target(p_student_id);
  actor public.app_users%rowtype;
  result jsonb;
begin
  select * into actor from public.app_users where id = (select auth.uid());
  if actor.role <> 'student' then
    insert into public.staff_audit(actor_id, action, subject_id) values (actor.id, 'view_coaching_timeline', target);
  end if;
  select coalesce(jsonb_agg(lpu_private.coaching_json(c) order by c.created_at desc, c.id desc), '[]'::jsonb)
    into result from public.coaching_records c
    where c.student_id = target and (actor.role <> 'student' or c.visibility = 'student');
  return result;
end;
$$;

create function public.coaching_create(p_student_id bigint, p_kind text, p_title text,
  p_detail text default '', p_due_date date default null, p_visibility text default 'student') returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  target uuid := lpu_private.coaching_target(p_student_id);
  actor public.app_users%rowtype;
  created public.coaching_records%rowtype;
begin
  select * into actor from public.app_users where id = (select auth.uid());
  if p_kind is null or p_kind not in ('goal', 'note', 'check_in', 'referral')
    or p_visibility is null or p_visibility not in ('student', 'mentor')
    or p_title is null or length(btrim(p_title)) not between 1 and 140
    or length(coalesce(p_detail, '')) > 2000 then
    raise exception 'Invalid coaching record' using errcode = '22023';
  end if;
  if actor.role = 'student' and (p_kind <> 'goal' or p_visibility <> 'student') then
    raise exception 'Not authorized' using errcode = '42501';
  end if;
  insert into public.coaching_records(student_id, author_id, kind, title, detail, due_date, visibility)
    values (target, actor.id, p_kind, btrim(p_title), btrim(coalesce(p_detail, '')), p_due_date, p_visibility)
    returning * into created;
  insert into public.staff_audit(actor_id, action, subject_id) values (actor.id, 'create_coaching_record', target);
  return lpu_private.coaching_json(created);
end;
$$;

create function public.coaching_update(p_student_id bigint, p_record_id bigint,
  p_status text default null, p_evidence_url text default null) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  target uuid := lpu_private.coaching_target(p_student_id);
  actor public.app_users%rowtype;
  updated public.coaching_records%rowtype;
begin
  select * into actor from public.app_users where id = (select auth.uid());
  if p_status is not null and p_status not in ('open', 'in_progress', 'completed') then
    raise exception 'Invalid action status' using errcode = '22023';
  end if;
  if p_evidence_url is not null and (length(btrim(p_evidence_url)) > 500
      or (btrim(p_evidence_url) <> '' and btrim(p_evidence_url) !~* '^https?://[^/[:space:]]+')) then
    raise exception 'Invalid evidence URL' using errcode = '22023';
  end if;
  select * into updated from public.coaching_records where id = p_record_id and student_id = target
    and kind = 'goal' and (actor.role <> 'student' or visibility = 'student') for update;
  if not found then raise exception 'Action plan item not found' using errcode = '42501'; end if;
  update public.coaching_records set status = coalesce(p_status, status),
    evidence_url = case when p_evidence_url is null then evidence_url else btrim(p_evidence_url) end,
    updated_at = now() where id = p_record_id returning * into updated;
  insert into public.staff_audit(actor_id, action, subject_id) values (actor.id, 'update_coaching_record', target);
  return lpu_private.coaching_json(updated);
end;
$$;

revoke all on function public.coaching_list(bigint), public.coaching_create(bigint,text,text,text,date,text),
  public.coaching_update(bigint,bigint,text,text) from public, anon, authenticated;
grant execute on function public.coaching_list(bigint), public.coaching_create(bigint,text,text,text,date,text),
  public.coaching_update(bigint,bigint,text,text) to authenticated;
commit;
