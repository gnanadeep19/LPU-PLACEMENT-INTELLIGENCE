-- Development-only smoke test. Prerequisites:
--   * migrations 001 and 002 applied to an isolated Supabase project;
--   * the synthetic student.demo account mapped to legacy_id 1;
--   * no other users concurrently modifying the project during this test.
-- This checks database authorization, not real JWT signature verification.
-- The private fixture and changes are rolled back at the end.
begin;

do $$
declare test_user uuid;
begin
  select id into test_user from public.app_users
    where legacy_id = 1 and username = 'student.demo' and role = 'student' and is_active;
  if test_user is null then raise exception 'Synthetic student.demo mapping is required'; end if;
  perform set_config('request.jwt.claims', jsonb_build_object('sub', test_user, 'role', 'authenticated')::text, true);
  perform set_config('request.jwt.claim.sub', test_user::text, true);
end;
$$;

-- Insert a deliberately private fixture as the database owner. The client
-- itself has no table-write privileges; this row will be rolled back.
with fixture as (
  insert into public.coaching_records(student_id, author_id, kind, title, visibility)
  select id, id, 'goal', 'Temporary private fixture', 'mentor' from public.app_users where legacy_id = 1
  returning id
)
select set_config('lpu.test_private_goal_id', id::text, true) from fixture;

set local role authenticated;
do $$
declare
  private_id bigint := current_setting('lpu.test_private_goal_id')::bigint;
  records jsonb;
  created jsonb;
  changed jsonb;
begin
  records := public.coaching_list(1);
  if exists (select 1 from jsonb_array_elements(records) r where (r->>'id')::bigint = private_id) then
    raise exception 'Private mentor record was exposed to student';
  end if;
  begin
    perform public.coaching_update(1, private_id, 'completed', null);
    raise exception 'Student unexpectedly updated a private record';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.coaching_create(1, 'note', 'Private test', '', null, 'mentor');
    raise exception 'Student unexpectedly created a private note';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.coaching_list(9223372036854775807);
    raise exception 'Unmapped student unexpectedly accessible';
  exception when insufficient_privilege then null;
  end;
  created := public.coaching_create(1, 'goal', 'Temporary public goal', '', null, 'student');
  changed := public.coaching_update(1, (created->>'id')::bigint, 'completed', null);
  if changed->>'status' <> 'completed' then raise exception 'Goal status did not update'; end if;
end;
$$;
reset role;
rollback;
