# Supabase migration: staged setup

## Current status

This is a **transition**, not a completed migration. Local login and SQLite
remain the application defaults. The separate development site uses Supabase
sign-in, Postgres coaching and mentor assignments, and Postgres notifications;
other dashboard records still depend on SQLite. Flask verifies each Supabase
access token and requires a matching active local account. Do not use the
hybrid configuration for real student records until migration, reconciliation,
and role-by-role access testing are complete.

The development project has been used to test a student-visible mentor update
and a study-resource notification. A scheduled reminder function and job were
also checked in a rollback-only test. This does not establish that all user
roles, notification cases, or dashboard workflows are ready for production.

## 1. Create a development project

1. Create an account at [Supabase](https://supabase.com/) and create a **separate
   development project**. Select a region suitable for your users and wait for
   it to finish provisioning.
2. In the project dashboard, find the project URL and publishable key. The
   publishable key identifies the project; it is not a user login token. Follow
   the dashboard's guidance for the project's current key format.
3. Keep the database password and secret/service-role key private. **Do not
   paste them into chat, frontend code, Git, or screenshots.** No secret key is
   needed to run the current local application.
4. Configure the intended Auth email/password and redirect settings according
   to [Supabase Auth documentation](https://supabase.com/docs/guides/auth).
   An invitation or password reset is needed for existing local users: their
   current usernames do not contain email addresses, and their password hashes
   must not simply be copied into Supabase Auth.
5. Disable public sign-up for this prototype; provision test accounts through
   an administrator-controlled flow. Users must not be able to choose their own
   role or cohort.

## 2. Inventory and protect local records

Stop making changes during any eventual cutover. First back up both local SQLite
databases using SQLite's backup facility, and verify the backups can be restored.
Do not delete or overwrite the originals. `backend/data/` contains the default
databases; environment settings may point elsewhere. Treat backups as sensitive.

From the project root, this read-only command prints **aggregate counts only**:

```powershell
python backend/supabase_migration_inventory.py
```

It opens both databases in SQLite read-only mode and reports missing tables,
null ownership references, and references to account IDs not present in the
local user table. It also counts local mentor assignments, assignment history,
study files and their total size, placement history, pending notification
intents, and unrecognized tables. It does not read session tokens or print file
contents. Use `--auth-db` and `--history-db` if your database paths
are configured differently. Resolve every missing or ambiguous identity before
migrating records; some historical anonymous assessments have no owner and
must not be assigned to a guessed student.

On November 3, 2026, a read-only check of the separate development site's
configured SQLite snapshots found 120 assessment rows, including 44 without an
owner, and two study-resource files totaling 248,230 bytes. A dry run using
synthetic UUIDs confirmed that the anonymous assessments remain unmapped and
the two files can be planned with synthetic account IDs. This does not verify
real account mappings, target permissions, or a live import. These counts are a
point-in-time development snapshot, not a count of records already in Supabase;
rerun the inventory before planning any cutover.

The same development snapshot was checked again after the resource schema was
installed: it contained two local study files and no pending resource
notifications. The newly created Postgres resource table was empty. These are
separate stores; do not switch the existing site until the files and account
identities have been reconciled and copied successfully.

The CV upload and mentor review workflow also stores files and review history
in the local `cv_submissions` SQLite table. It has not been migrated to
Supabase and is not covered by the resource-only importer. The full importer
detects a non-empty unrecognized source table and refuses an incomplete import;
CV submissions need their own migration and reconciliation before cutover.

## 3. Understand the prepared database schema

`supabase/migrations/202610310001_initial.sql` creates the planned Postgres
tables, including an `app_users` mapping from Supabase Auth UUIDs to legacy
integer IDs. It enables Row Level Security and denies direct client access by
default. Authenticated users can read only their own active `app_users` row and
read/update only `read_at` on their own notifications. The other tables remain
inaccessible to browser clients; additional role- and cohort-scoped access and
the backend data layer are not yet implemented.

The schema includes notification triggers for new student-visible Postgres
coaching records and completed goals. These triggers run only when coaching is
stored in Postgres, not when it is stored in SQLite. The importer suppresses
historical coaching notifications during its transaction.

Review and test this migration in the new development project before applying
it. It is a one-time initial migration and is not intended to be rerun over an
existing schema. Applying it does **not** migrate records or change this app's
login. A server-side privileged database connection or API can bypass RLS, so
Flask must enforce authorization itself even when using a server secret.

## 3a. Enable transition mode for synthetic accounts only

After the SQL is reviewed and applied to a new development project, an
authorized administrator can create a synthetic Supabase Auth user and an
`app_users` row linked to that user's UUID. Its `legacy_id` must match the
existing local user ID, and `username`, `role`, `cohort`, and active status
must match the local account exactly. No automatic account linking or role
promotion is implemented. Do not use unverified email matching to link users.

For a synthetic test account, `python backend/manage_users.py list-users` shows
the local account ID and role. After an administrator has created the test Auth
user, get that user's UUID from the Supabase Authentication dashboard. The
trusted administrator can then insert a matching row in the SQL editor, replacing
all placeholders below with the *verified test account's* values:

```sql
insert into public.app_users (id, legacy_id, username, display_name, role, cohort)
values ('<auth-user-uuid>', 1, '<local-username>', '<display-name>', 'student', '<local-cohort>');
```

If the local cohort is empty, use SQL `null` instead of a quoted string. A
mentor's cohort is required. Provision elevated roles only after an authorized
administrator verifies the assignment. A mismatch prevents sign-in rather than
granting access.

In the **frontend** directory, copy `.env.example` to `.env.local` and set:

```dotenv
VITE_AUTH_PROVIDER=supabase
VITE_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=YOUR-PUBLISHABLE-KEY
```

For the **backend**, set these environment variables before starting Flask
(the Python app reads process environment variables; it does not load `.env`
automatically):

```powershell
$env:AUTH_PROVIDER = 'supabase'
$env:SUPABASE_URL = 'https://YOUR-PROJECT.supabase.co'
$env:SUPABASE_PUBLISHABLE_KEY = 'YOUR-PUBLISHABLE-KEY'
python backend/app.py
```

Use the same project URL and publishable key in both locations. These are public
project identifiers, not a service-role/secret key. Restart both servers after
changing configuration. The login form accepts the Supabase account's email.
The local username/password login is disabled on the backend in Supabase mode;
missing or inconsistent configuration fails closed. The browser SDK stores
the session in `sessionStorage` for this tab and refreshes tokens; scripts on
the page can access this storage, so deploy a restrictive Content Security
Policy and review XSS controls. Production CSP must permit the exact Supabase
project origin in `connect-src`. This prototype does not yet provide an
institutional SSO or a production-ready session security review.

To return to local development, remove the Vite settings and restart with
`AUTH_PROVIDER=local` (or unset it). Keep the local databases and backups.

## 4. Identity and data migration plan

1. With authorized owners, build a protected mapping of each existing integer
   user ID to a verified email and a newly created Supabase Auth UUID. Do not
   use a client-supplied role, email claim alone, or editable user metadata to
   grant a mentor or admin role. An authorized administrator must provision the
   `app_users` role, cohort, and active state.
2. Test invites or password-reset onboarding for a small synthetic cohort.
   Supabase sends invitations only when an administrator deliberately triggers
   them. Existing local passwords are not transferred by this preparation.
3. Review `backend/supabase_migrate.py`, the staged one-time importer. It maps
   user references in assessments, coaching records, profile settings, evidence,
   corrections, placement events, placement-stage history, study resources, and audit logs. It preserves legacy IDs,
   timestamps, and private-note visibility. Its default is an offline dry run;
   it has **not yet been tested against a real Supabase project**. See the
   next section before attempting any import.
4. Compare source and target row counts, references, and representative records
   using synthetic data. Test rollback using the untouched backups. Plan a
   read-only cutover window so new writes are not lost.
5. Only after the Flask storage layer, login/session handling, notifications,
   and access tests have been migrated, switch the application to the new
   database and run the same checks again.

## 5. Controlled importer workflow

This tool is prepared for a **fresh development database only**. Do not use it
on a production project until a synthetic-data rehearsal, security review and
restore test pass. Run it on a trusted machine with protected local database
backups. Stop the app and any other writers for the entire export/cutover so
the two SQLite source databases cannot change while the plan is built.

Create a protected local CSV containing the **administrator-verified** mappings
from local accounts to existing Supabase Auth UUIDs. Do not commit this file or
share it in chat. Replace these illustrative values with verified test values:

```csv
legacy_id,auth_user_id
1,4d9e8e7d-b06c-4c79-8873-8a1d7ba61c08
```

Run a local dry run from the project root:

```powershell
python backend/supabase_migrate.py --mapping C:\path\to\private-mapping.csv
```

Use Python 3.11 or newer for the migration tool; it uses SQLite's incremental
blob reader. The project's development environment uses Python 3.13.

The report contains counts only. It does not print personal records, open a
network connection, create tables, change SQLite, or upload anything. It skips
rows with missing required user mappings and reports their number; it never
guesses an owner. Its mapping checks do not prove the real-world identity is
correct: the administrator must establish that separately.

The staged placement-history and resource schemas are in
`supabase/migrations/202611030002_placement_history.sql` and
`supabase/migrations/202611030003_study_resources.sql`. They must be reviewed
and applied to a separate empty development target before using the importer.
The resource table stores files as bounded Postgres `bytea` values and denies
direct client access. The staged migration
`supabase/migrations/202611030004_study_resource_api.sql` adds resource RPCs
with role and student-access checks. `RESOURCE_STORE=supabase` selects the new
Flask path and requires Supabase authentication and coaching. On November 3,
2026, migrations 003 and 004 were applied to the separate development project.
A read-only check found RLS enabled, authenticated direct table SELECT denied,
authenticated RPC execution granted, anonymous RPC execution denied, and zero
files in Postgres. The option is not enabled on the current development site;
an end-to-end browser test and migration of its existing files still remain.
Creating these tables or changing the setting does not migrate existing files.

The new path saves a resource and its notification in one transaction and uses
a client upload key to prevent duplicate uploads after an uncertain retry. The
5 MB limit remains. Group uploads are separate transactions per student.
The default `RESOURCE_STORE=sqlite` preserves the existing local behavior.

On November 3, 2026, a rollback-only test of the staged resource migrations
in the separate development project passed function checks for an authorized
mentor upload, idempotent retry, notification creation, student download, and
cross-student denial. A subsequent read-only check confirmed that the resource
table and RPC were absent after rollback and no test notification remained.
The functions were also exercised under the `authenticated` Postgres role in a
separate rollback-only transaction. This verified the RPC grants, denied direct
table access, student download and cross-student denial. A separate local test
instance with `RESOURCE_STORE=supabase` was subsequently used for a mentor
upload; Postgres confirmed one resource and its matching notification for the
intended demo student. A different student saw no shared resources. The
intended recipient saw the notification and resource in the browser; the
download endpoint returned HTTP 200 and the user confirmed that the file was
saved. The existing local files have not been migrated. The test also exposed
intermittent dashboard request timeouts, which require investigation before
enabling the new storage path on the current development site.

`backend/supabase_resource_migrate.py` is a separate, dry-run-first utility for
copying only study resources. It refuses unmapped authors or students, pending
resource-notification intents and changed source files. By default it also
refuses a non-empty target. The explicit `--allow-existing` option preserves
existing non-imported resources, but stops if a prior import is present or the
same student, author and file contents already appear in Postgres. It verifies
approved account mappings and uses a transaction. A privileged TLS-verified
database connection is needed to apply it; the database URL belongs only in
the local environment. This utility does not migrate the rest of the dashboard
or switch the running app. Stop resource writes, retain verified backups,
rehearse against synthetic data, and reconcile identities and file counts before
considering a cutover.

The resource plan stores metadata and SHA-256 hashes in memory but does not
retain file contents or print them. Within the same apply invocation it reads
one file at a time, checks its metadata and hash, and rejects a changed file or
changed file inventory. Each file must be non-empty and at most 5 MB. These
checks do not replace stopping all local writers: a separate dry-run command
creates a new plan, and changes can occur after a read snapshot is opened.

The dry run also lists source tables that this importer does not yet migrate.
The importer refuses to apply if any such table contains records, even with
`--allow-unmapped`. This includes local mentor assignments and assignment
events, notification outbox records, and
any newly discovered non-empty table. These records need an implemented and
tested migration and reconciliation before cutover. Local sessions are
intentionally excluded; users must establish new sessions.

The current development site is hybrid: some coaching records and mentor
assignments are authoritative in Supabase, while other records remain local.
A local inventory alone cannot establish what is already present remotely. The
one-time importer also requires an empty target, so do not point it at the
existing populated development project or treat it as a synchronization tool.

Before a synthetic-data rehearsal, an administrator must apply the reviewed
schema, create the Auth accounts, and provision matching `app_users` records.
The target usernames, roles, cohorts and active status must match SQLite. The
importer requires the target data tables to be empty and refuses to merge or
overwrite records. It locks them during the operation, imports within one
transaction, and temporarily disables the coaching notification trigger within
that transaction so historical records do not generate new notifications. A
failure rolls back both records and trigger changes. This is a one-time import,
not an incremental synchronization tool.

The optional `backend/requirements-migration.txt` contains the Postgres driver.
When you are ready to rehearse, configure `SUPABASE_DATABASE_URL` **locally as a
secret environment variable** and run the same command with `--apply`. The tool
requires a TLS-verified connection and a database role able to lock tables and
manage the trigger. It does not accept a connection string on the command line.
Do not paste the database URL into chat or commit it to source control.

By default, the importer refuses to apply if an account or record is unmapped.
The explicit `--allow-unmapped` option leaves those records in SQLite; it does
not upload, delete, or assign them. Only use this after reviewing the missing
records and keeping a restorable backup. Missing source tables always stop an
import. Reconcile destination counts before making any cutover decision.

## 6. Remaining application work

- Review and test `supabase/migrations/202610310002_coaching_rpc.sql` in an
  isolated development project before applying it. It adds security-definer
  coaching RPCs that enforce the active Supabase profile's student/cohort role
  at the database boundary, even if called directly rather than through Flask.
  It must not be used with real users until direct-call, cross-cohort, private
  note, notification, error and concurrency tests pass on a live database.
- The experimental backend setting `COACHING_STORE=supabase` switches **only**
  coaching list/create/update to these RPCs; it also requires
  `AUTH_PROVIDER=supabase`. Its default remains `sqlite`, and it never falls
  back to SQLite when Postgres is unavailable. All other workflows, including
  assessment history, profiles, placement records and some audit views, remain
  SQLite-based. Each user and student whose records need to be accessed must
  first have an administrator-approved `app_users` mapping. Provisioning only
  one student is not enough to test a mentor workflow.
- Existing SQLite coaching records are not copied when this option is enabled.
  Import reconciled records first or explicitly use a fresh synthetic dataset;
  switching the flag without doing so would make the old coaching history
  appear empty. Postgres coaching writes and notifications commit together,
  but other SQLite operations and audit views remain separate until fully
  migrated. Do not make a production cutover in this hybrid mode.
- Complete live integration testing of Supabase login, refresh, logout,
  deactivation, and outage behavior using distinct synthetic accounts. The
  transition verifies the access token on each Flask request and loads role,
  cohort, and active status from the server-provisioned profile. Its strict
  legacy-ID mapping must be removed or redesigned when SQLite is retired.
- Replace all SQLite-specific reads and writes in `auth.py`, `history.py`, and
  `collaboration.py` with a tested Postgres data layer. Preserve authorization,
  transactions, and audit events. Existing integer route identifiers need an
  explicit, consistent compatibility plan.
- Test the Postgres coaching data layer and notification triggers using
  separate synthetic accounts, including recipient-only reads/updates against
  the live project's RLS, before enabling the optional path.
  The bell UI uses the user's Supabase session. Never notify students about
  private mentor notes. A development reminder scheduler was installed and
  its idempotency was checked in a rollback-only test; actual scheduled
  delivery still needs an end-to-end test with synthetic accounts.
- Test cross-student access, mentor cohort boundaries, private notes, admin-only
  changes, notification ownership, expired tokens, revoked/deactivated users,
  outages, duplicate events, and rollback. Test the SQL policies in an actual
  Supabase development project using distinct authenticated accounts.
- Use only synthetic or authorized data, enable HTTPS and configure deployment
  secrets securely before inviting users. Review retention, consent, and access
  with the data owner.

Reference: [server-side token verification](https://supabase.com/docs/reference/python/auth-getuser),
[row-level security](https://supabase.com/docs/guides/database/postgres/row-level-security),
and [user invitations](https://supabase.com/docs/guides/auth/users).
