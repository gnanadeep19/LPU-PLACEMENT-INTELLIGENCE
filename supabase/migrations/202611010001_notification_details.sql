-- Include student-visible coaching details in notifications. Private notes are
-- excluded by the same visibility and kind checks as the original trigger.
begin;

create or replace function public.notify_coaching_change() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'INSERT' and new.visibility = 'student'
     and new.kind in ('goal', 'check_in') and new.author_id <> new.student_id
     and exists (select 1 from public.app_users u where u.id = new.student_id and u.is_active) then
    insert into public.notifications(recipient_id, kind, title, message, event_key)
      values (new.student_id, 'coaching_update', new.title,
              coalesce(nullif(btrim(new.detail), ''), 'No description provided.'),
              'coaching-created:' || new.id::text)
      on conflict (recipient_id, event_key) do nothing;
  elsif tg_op = 'UPDATE' and old.status is distinct from new.status
        and new.status = 'completed' and new.kind = 'goal'
        and new.visibility = 'student' and new.author_id <> new.student_id
        and exists (
          select 1 from public.app_users author join public.app_users student on student.id = new.student_id
          where author.id = new.author_id and author.is_active and student.is_active
            and (author.role in ('admin', 'placement_officer')
                 or (author.role = 'mentor' and author.cohort = student.cohort))
        ) then
    insert into public.notifications(recipient_id, kind, title, message, event_key)
      values (new.author_id, 'goal_completed', 'Goal completed',
              'A student goal you created was marked complete. Review the timeline.',
              'goal-completed:' || new.id::text)
      on conflict (recipient_id, event_key) do nothing;
  end if;
  return new;
end;
$$;

-- Upgrade existing generic notifications only when the associated record is
-- still student-visible and belongs to the original notification recipient.
update public.notifications n
set title = c.title,
    message = coalesce(nullif(btrim(c.detail), ''), 'No description provided.')
from public.coaching_records c
where n.kind = 'coaching_update'
  and n.title = 'New mentor update'
  and n.message = 'A mentor added a student-visible update to your timeline.'
  and n.event_key = 'coaching-created:' || c.id::text
  and n.recipient_id = c.student_id
  and c.visibility = 'student'
  and c.kind in ('goal', 'check_in')
  and c.author_id <> c.student_id;

commit;
