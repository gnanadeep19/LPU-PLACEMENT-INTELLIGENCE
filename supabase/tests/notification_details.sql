-- Run only in the isolated development project after migrations 001-003.
-- All fixtures and notifications are rolled back.
begin;
do $$
declare
  student uuid;
  mentor uuid;
  meeting_id bigint;
  private_id bigint;
  empty_id bigint;
  n public.notifications%rowtype;
begin
  select id into student from public.app_users where username = 'student.demo' and role = 'student' and is_active;
  select id into mentor from public.app_users where username = 'mentor.cse' and role = 'mentor' and is_active;
  if student is null or mentor is null then raise exception 'Demo student and mentor accounts are required'; end if;

  insert into public.coaching_records(student_id, author_id, kind, title, detail, visibility)
    values (student, mentor, 'check_in', 'Test meeting title', 'Test meeting description', 'student')
    returning id into meeting_id;
  select * into n from public.notifications
    where recipient_id = student and event_key = 'coaching-created:' || meeting_id::text;
  if not found or n.title <> 'Test meeting title' or n.message <> 'Test meeting description' then
    raise exception 'Student-visible meeting details missing from notification';
  end if;

  insert into public.coaching_records(student_id, author_id, kind, title, detail, visibility)
    values (student, mentor, 'check_in', 'Private meeting', 'Private details', 'mentor') returning id into private_id;
  if exists (select 1 from public.notifications where event_key = 'coaching-created:' || private_id::text) then
    raise exception 'A private coaching record generated a notification';
  end if;

  insert into public.coaching_records(student_id, author_id, kind, title, detail, visibility)
    values (student, mentor, 'goal', 'No description', '', 'student') returning id into empty_id;
  select * into n from public.notifications where recipient_id = student and event_key = 'coaching-created:' || empty_id::text;
  if not found or n.message <> 'No description provided.' then raise exception 'Missing description fallback'; end if;

  update public.coaching_records set status = 'completed' where id = empty_id;
  if not exists (select 1 from public.notifications where recipient_id = mentor
      and event_key = 'goal-completed:' || empty_id::text) then
    raise exception 'Goal completion notification no longer works';
  end if;
end;
$$;
rollback;
