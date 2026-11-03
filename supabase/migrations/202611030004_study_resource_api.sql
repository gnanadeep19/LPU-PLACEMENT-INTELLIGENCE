-- Staged Postgres resource API. Requires 202611030003_study_resources.sql and
-- the cross-cohort coaching_target function. Direct table access stays denied.
begin;

-- A client-generated key makes a retry after an uncertain network failure safe.
-- Imported legacy records keep a null key and are not changed by this index.
alter table public.study_resources add column upload_key uuid;
create unique index study_resources_upload_key_idx
  on public.study_resources(student_id,author_id,upload_key) where upload_key is not null;

create function lpu_private.study_resource_json(p_record public.study_resources) returns jsonb
language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('id', p_record.id, 'student_id', student.legacy_id,
    'author_id', author.legacy_id, 'title', p_record.title, 'description', p_record.description,
    'filename', p_record.filename, 'category', p_record.category,
    'size', octet_length(p_record.content), 'created_at', p_record.created_at)
  from public.app_users student, public.app_users author
  where student.id=p_record.student_id and author.id=p_record.author_id;
$$;
revoke all on function lpu_private.study_resource_json(public.study_resources) from public, anon, authenticated;

create function public.study_resource_list(p_student_id bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare target uuid := lpu_private.coaching_target(p_student_id); actor public.app_users%rowtype; result jsonb;
begin
  select * into actor from public.app_users where id=(select auth.uid());
  if actor.role <> 'student' then
    insert into public.staff_audit(actor_id,action,subject_id) values(actor.id,'view_study_resources',target);
  end if;
  select coalesce(jsonb_agg(lpu_private.study_resource_json(r) order by r.created_at desc,r.id desc),'[]'::jsonb)
    into result from public.study_resources r where r.student_id=target;
  return result;
end $$;

create function public.study_resource_create(p_student_id bigint, p_title text, p_description text,
  p_filename text, p_category text, p_content_base64 text, p_upload_key uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare target uuid := lpu_private.coaching_target(p_student_id); actor public.app_users%rowtype;
  content_bytes bytea; extension text; created public.study_resources%rowtype;
begin
  select * into actor from public.app_users where id=(select auth.uid());
  if actor.role not in ('mentor','admin','placement_officer') then
    raise exception 'Not authorized' using errcode='42501';
  end if;
  if p_title is null or length(btrim(p_title)) not between 1 and 140 or length(coalesce(p_description,'')) > 2000
    or p_filename is null or p_filename !~ '^[A-Za-z0-9_.-]{1,255}$' or p_filename in ('.','..')
    or p_category is null or p_category not in ('General','Coding','Technical skills','Aptitude','Communication','Resume','Interview')
    or p_upload_key is null or p_content_base64 is null or length(p_content_base64) not between 4 and 6990508
    or p_content_base64 !~ '^[A-Za-z0-9+/]*={0,2}$' then
    raise exception 'Invalid study resource' using errcode='22023';
  end if;
  extension := lower(substring(p_filename from '\.([^.]+)$'));
  if extension is null or extension not in ('pdf','docx','pptx','txt','png','jpg','jpeg') then
    raise exception 'Unsupported study resource type' using errcode='22023';
  end if;
  content_bytes := decode(p_content_base64,'base64');
  if octet_length(content_bytes) not between 1 and 5242880
    or (extension='pdf' and substring(content_bytes from 1 for 5) <> decode('255044462d','hex'))
    or (extension in ('docx','pptx') and substring(content_bytes from 1 for 4) <> decode('504b0304','hex'))
    or (extension='png' and substring(content_bytes from 1 for 8) <> decode('89504e470d0a1a0a','hex'))
    or (extension in ('jpg','jpeg') and substring(content_bytes from 1 for 3) <> decode('ffd8ff','hex'))
    or (extension='txt' and position(decode('00','hex') in content_bytes) > 0) then
    raise exception 'Invalid study resource content' using errcode='22023';
  end if;
  insert into public.study_resources(student_id,author_id,title,description,filename,category,content,created_at,upload_key)
    values(target,actor.id,btrim(p_title),btrim(coalesce(p_description,'')),p_filename,p_category,content_bytes,now(),p_upload_key)
    on conflict(student_id,author_id,upload_key) where upload_key is not null do nothing
    returning * into created;
  if found then
    insert into public.notifications(recipient_id,kind,title,message,event_key)
      values(target,'study_resource','New study resource',created.title,'study-resource-pg:' || created.id::text)
      on conflict(recipient_id,event_key) do nothing;
    insert into public.staff_audit(actor_id,action,subject_id) values(actor.id,'share_study_resource',target);
  else
    select * into created from public.study_resources
      where student_id=target and author_id=actor.id and upload_key=p_upload_key;
    if not found or created.title is distinct from btrim(p_title)
      or created.description is distinct from btrim(coalesce(p_description,''))
      or created.filename is distinct from p_filename or created.category is distinct from p_category
      or created.content is distinct from content_bytes then
      raise exception 'Upload key is already in use' using errcode='22023';
    end if;
  end if;
  return lpu_private.study_resource_json(created) || jsonb_build_object('notification_sent',true);
end $$;

create function public.study_resource_download(p_student_id bigint,p_resource_id bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare target uuid := lpu_private.coaching_target(p_student_id); actor public.app_users%rowtype;
  resource public.study_resources%rowtype;
begin
  select * into actor from public.app_users where id=(select auth.uid());
  select * into resource from public.study_resources where id=p_resource_id and student_id=target;
  if not found then raise exception 'Resource unavailable' using errcode='42501'; end if;
  if actor.role <> 'student' then
    insert into public.staff_audit(actor_id,action,subject_id) values(actor.id,'download_study_resource',target);
  end if;
  return jsonb_build_object('filename',resource.filename,'content_base64',replace(encode(resource.content,'base64'),E'\n',''));
end $$;

create function public.study_resource_delete(p_student_id bigint,p_resource_id bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare target uuid := lpu_private.coaching_target(p_student_id); actor public.app_users%rowtype;
  resource public.study_resources%rowtype;
begin
  select * into actor from public.app_users where id=(select auth.uid());
  if actor.role not in ('mentor','admin','placement_officer') then
    raise exception 'Not authorized' using errcode='42501';
  end if;
  select * into resource from public.study_resources where id=p_resource_id and student_id=target for update;
  if not found or (resource.author_id<>actor.id and actor.role<>'admin') then
    raise exception 'Resource unavailable' using errcode='42501';
  end if;
  delete from public.study_resources where id=resource.id;
  insert into public.staff_audit(actor_id,action,subject_id) values(actor.id,'delete_study_resource',target);
  return jsonb_build_object('deleted',true);
end $$;

revoke all on function public.study_resource_list(bigint), public.study_resource_create(bigint,text,text,text,text,text,uuid),
  public.study_resource_download(bigint,bigint), public.study_resource_delete(bigint,bigint) from public, anon, authenticated;
grant execute on function public.study_resource_list(bigint), public.study_resource_create(bigint,text,text,text,text,text,uuid),
  public.study_resource_download(bigint,bigint), public.study_resource_delete(bigint,bigint) to authenticated;
commit;
