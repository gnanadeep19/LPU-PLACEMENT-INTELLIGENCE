# LPU Placement Intelligence — Product Development Plan

## Product goal

Help students decide what to improve next, help mentors choose timely support, and help placement administrators understand program-level progress. The platform is decision support: a readiness estimate must never be presented as a placement result, guarantee, or automatic eligibility decision.

## Current project baseline

This repository already provides a React/Vite client, Flask API, local SQLite persistence, role-based demo login, readiness predictions and explanations, student action plans and evidence submissions, mentor cohort workflows, admin placement pipeline, data quality and model-monitoring views, and basic access/audit controls. The existing governance notes identify unresolved source and label provenance, unverified role requirements, and missing institutional identity, consent, and retention integrations. Treat this as a functional prototype, not a production LPU service.

## Phased delivery plan

| Phase | Scope | Acceptance criteria | Status |
|---|---|---|---|
| 0. Product and data foundation | Confirm user journeys, define shared terminology, inventory data sources, document the current model target and limitations. | Readiness, profile coverage, placement outcome, and role criteria have separate definitions; every displayed metric has a source and period. | Baseline documented; institutional definitions still need an owner. |
| 1. Student readiness workspace | Personal readiness overview, input coverage, evidence status, target-role comparison, measurable roadmap, progress history, correction requests and preparation resources. | A student can inspect inputs, see prioritized gap/evidence/action/effort/due date/progress measure, submit evidence, request a correction, and understand uncertainty. | Implemented for recommendations, evidence, correction requests, history and role guide; resume/interview scheduling are still preparation-plan items. |
| 2. Mentor support workflow | Assigned mentee roster, filters, explainable support queue, profile detail, coaching notes with audience labels, goals, check-ins, referrals and cohort insights. | Mentors see only their authorized cohort; every support signal includes a reason; actions and follow-ups persist and appear in student/mentor views as intended. | Core loop exists; access boundaries now have explicit tests. Confirm institutional assignment rules before deployment. |
| 3. Placement operations | Cohort overview, placement stages, program filters, mentor coverage and follow-up oversight. | Placement outcomes remain separate from readiness estimates; stage updates include who/when and can be audited; reports state denominators. | Demo pipeline and metric denominator labels exist; institutional process and definitions need placement-office review. |
| 4. Data quality and model governance | Coverage checks, correction requests, data provenance, model version, evaluation period, sample size, calibration, subgroup review, drift and approval record. | No model-quality claim appears without a defined outcome, evaluation set, sample size and model version; missing data is visible before comparing groups. | Version is stored with assessments; target label and limitations are disclosed; provenance, external validation and subgroup review remain blocking inputs. |
| 5. Security and institutional integration | LPU identity/SSO and MFA, authorized roster sync, consent/notice, retention/deletion, export controls, operational monitoring, backups and incident response. | Security/privacy review passes; permissions and audit events are validated; real student data has an approved source, purpose, retention and access policy. | Not implemented; do not connect production student data before approval. |
| 6. Pilot and rollout | Synthetic-data demo, supervised pilot, user feedback, accessibility review, model review, staged release and support ownership. | Named product/data/model/security/operations owners; pilot success measures and rollback path; release criteria documented and met. | Isolated synthetic demo seeding, reset flow and three role walkthroughs documented. Pilot remains planned. |

## Shared product rules

1. Use the same readiness and skill definitions across all three workspaces.
2. Keep readiness, evidence coverage, confidence, and real placement outcomes as distinct concepts. Do not label raw model probability as an individual's chance of placement unless the model has been calibrated and validated for that exact outcome and population.
3. Every recommendation should show the gap, evidence, practical next action, and a way to measure progress.
4. Mark evidence as student-reported, imported, or verified and show its age. Never imply institutional verification when none occurred.
5. Students can review and correct profile data and request human review. Mentors see only their assigned students; admins default to aggregate information.
6. Use supportive language. Scores may guide support, but must not automatically exclude a student.

## UI design direction

Use a calm, high-contrast university product interface: navy/ink foundation, warm orange action color, restrained semantic colors, generous spacing, clear page titles, compact metric cards, consistent table actions, and responsive layouts. Each role gets a task-oriented landing view rather than a generic analytics wall. Keep primary actions visible, show loading/empty/error states, preserve keyboard and screen-reader support, and use charts only when a textual equivalent is available. On small screens, convert wide tables to scrollable or stacked layouts without hiding key actions.

### Workspace information architecture

- **Student:** Readiness overview → evidence and coverage → role gaps → action plan → progress → profile and assessments.
- **Mentor:** Support queue → assigned roster → selected student profile/timeline → coaching actions → cohort patterns.
- **Admin/placement:** Program overview → placement pipeline → data quality → mentor program → model monitoring → access and audit.

## Suggested delivery sequence for the next development cycle

1. Confirm model label/source and role requirements with the data owner and placement office.
2. Improve the student experience and close any mismatch between recommendations and stored action-plan fields.
3. Validate mentor cohort assignment, private/student-visible note behavior, and due-date notifications.
4. Add placement-stage history and definitions approved by placement staff.
5. Complete data quality remediation and document provenance; preserve raw source files until approved transformations are signed off.
6. Evaluate the model on a held-out, representative dataset; report calibration and error rates by approved cohort/role, with sample sizes and limitations.
7. Integrate institutional identity and approved data feeds, then complete security/privacy/accessibility review.
8. Run a synthetic-data demonstration and a supervised pilot before any wider rollout.

## Risks and dependencies

- Current dataset provenance and prediction target are not verified for LPU placement decisions.
- Project-defined job profiles are not official employer or placement-cell criteria.
- Self-reported values can be incomplete, stale, or inaccurate; coverage must not be confused with ability.
- Subgroup reporting requires privacy suppression and approved minimum cohort thresholds.
- SSO, consent, retention, and institutional data feeds require university owners and cannot be completed by a frontend change alone.

## Changes delivered for the requested improvement set

- Recommendations now expose evidence, effort, suggested due date, and progress measure; the student UI limits surfaced suggestions to three and stores that context when added to the plan.
- The prediction includes model version, the dataset target label, evaluation row counts/date when available, and an explicit provenance/generalization disclaimer. Assessment history persists the producing model version.
- Students can submit profile correction requests. Administrators can review/decline them, with the request and decision recorded in the audit log. Review does not silently mutate a numeric model profile; an approved profile update requires a new assessment.
- Mentor workflows, actual placement stages, admin data-quality and model-monitoring views, guided role tours, and advisory banners build on existing flows.
- An isolated synthetic demo seed/reset script and guide are included. The demo usernames are documented; the shared password is chosen locally and never committed.
- Backend access/failure tests cover cross-student reads, mentor cohort boundaries, private-note creation, placement-stage authorization, invalid dates/links, correction review permissions, and session expiration.

Some requested capabilities remain dependent on approved institutional data or require a future product increment: external model validation on an LPU-representative holdout set; meaningful confidence intervals and subgroup evaluation; institutional SSO, consent/retention, verified imports; and native resume-review/interview-scheduling integrations. The app must not imply these are already validated or connected.

## Definition of done for a production pilot

The product owner signs off on workflows and terms; the institutional data owner approves source, purpose, and retention; the model owner documents validation and limitations; security/privacy reviewers approve identity, access, logging, exports and incident handling; placement staff approve role criteria and pipeline definitions; and operations has monitoring, backup, support, and rollback procedures. Until then, use synthetic or explicitly authorized de-identified data and identify the app as a prototype.
