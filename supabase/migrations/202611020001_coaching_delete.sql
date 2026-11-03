-- Allows an author to remove their own coaching item. The existing target
-- function independently enforces active-user, student and cohort checks.
begin;
create or replace function public.coaching_delete(p_student_id bigint, p_record_id bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  target uuid := lpu_private.coaching_target(p_student_id);
  actor public.app_users%rowtype;
  removed public.coaching_records%rowtype;
begin
  select * into actor from public.app_users where id = (select auth.uid()) and is_active;
  if not found then raise exception 'Not authorized' using errcode = '42501'; end if;
  delete from public.coaching_records where id = p_record_id and student_id = target
    and author_id = actor.id and (actor.role <> 'student' or (kind = 'goal' and visibility = 'student'))
    returning * into removed;
  if not found then raise exception 'Not authorized or record unavailable' using errcode = '42501'; end if;
  insert into public.staff_audit(actor_id, action, subject_id) values (actor.id, 'delete_coaching_record', target);
  return jsonb_build_object('id', removed.id);
end;
$$;
revoke all on function public.coaching_delete(bigint,bigint) from public, anon, authenticated;
grant execute on function public.coaching_delete(bigint,bigint) to authenticated;
commit;
