# Dashboard improvements and remaining work

The student overview now shows up to three active or suggested actions and a compact activity timeline. Suggestions are not saved goals: add them to the action plan to set a due date. The resume checklist and interview-practice planner use student-visible coaching goals. Practice dates are personal plans, not booked meetings.

Mentors can filter assigned students separately, see a follow-up queue, and share one resource with several students in their permitted roster. The server checks access independently for every recipient. Files remain limited to 5 MB and stored in the existing local SQLite database. A group upload can partially succeed; the interface lists failures and asks the mentor to retry only those students.

Administrators have a separate mentor assignment view, a cohort and role comparison over assessed profiles, placement-stage history for changes made after this update, and an explicit audit loading error. Comparison rows are suppressed across the whole dimension if a group is below the minimum. This is a basic disclosure control, not a complete privacy review. Older placement changes cannot be reconstructed; the previous current stage is retained when it is first updated after this change.

## Development Supabase migration

`supabase/migrations/202611030001_goal_reminders.sql` defines a scope-checked resource notification RPC and schedules goal reminders with `pg_cron`. It must be applied after the earlier coaching and cross-cohort migrations to the separate development project. It schedules reminders at 08:30 India time, and creates at most one notification per goal, due date, reminder phase and recipient. It does not send email or SMS.

The migration was applied to the separate development project on November 3, 2026. The prerequisite check confirmed the coaching and assignment tables, access function, and `pg_cron`. A read-only verification found one active daily job, authenticated access to the scoped resource-notification function, no anonymous access to it, and no authenticated-user access to the scheduler function.

The demo mentor shared a synthetic resource and the demo student saw its notification in the application. A rollback-only SQL test created a temporary upcoming goal, verified that both the demo student and mentor received reminder rows, reran the reminder function to verify deduplication, and rolled back the test data. On November 3 the scheduler had no recorded automatic runs; check `cron.job_run_details` after the next scheduled time to verify that the job actually runs. Confirm deactivated users and revoked cross-cohort assignments do not receive new reminders. Do not use real student records until access and retention policies have been approved.

Resource files still commit to SQLite while notifications are sent to Postgres in a separate operation. New Supabase-mode uploads now commit a pending notification intent with the file. If delivery fails or the server stops before delivery, the uploader or an administrator can retry it from that student's resource list without re-uploading the file. The remote notification uses an idempotent event key. The retry holds a SQLite write lock while the remote request runs, so a slow outage can delay other local writes. Existing resources uploaded before this outbox was introduced have no delivery status, and failures for other recipients in a group share must be retried from each student's list. Delivery is not automatic; a secure background worker, reconciliation, and fully migrated storage are still needed for production. The rollback test validates function behavior, not automatic scheduler execution or end-to-end delivery of a scheduled reminder.

## Remaining before production

- Complete and rehearse the SQLite-to-Postgres migration, including assessments, evidence, placement history, resources, audit records and identity mapping. Reconcile counts, test backup and rollback, and test access boundaries against a live test database.
- Implement administrator-controlled onboarding, account recovery and deactivation, and complete an institutional identity and security review.
- Validate the model and its labels on a representative dataset. Approve role requirements, privacy thresholds, reporting definitions and retention policies.
- Run end-to-end role, mobile, keyboard and screen-reader tests. Validate scheduling, notification outage handling, repeated submissions and group resource sharing against the deployed development services.
