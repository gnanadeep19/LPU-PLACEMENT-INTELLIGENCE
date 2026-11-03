# UI design guide

## Experience principles

- Lead with the task each role needs to complete, not a collection of charts.
- Make readiness, evidence coverage, confidence, and placement outcome visually distinct.
- Put the next useful action beside the gap it addresses.
- Show where information came from and when it was last updated.
- Use plain language, supportive status labels, and clear empty/loading/error states.
- Preserve keyboard navigation, semantic headings, visible focus, accessible contrast, and text equivalents for charts.

## Visual system

Keep the existing navy and orange identity, reduce decorative gradients and glass effects in dense data views, and use solid surfaces for tables and forms. Use consistent spacing, card radius, heading scale, button hierarchy, status palette, and responsive breakpoints. Reserve orange for primary actions and meaningful emphasis; do not use color alone to communicate status.

## Role landing pages

### Student

1. Page title with target role and last-updated state.
2. Readiness score and plain-language interpretation.
3. Separate profile coverage/evidence quality card with missing or stale items.
4. Strengths and highest-priority gaps with evidence and next actions.
5. Role skill matrix, manageable weekly plan, and progress timeline.
6. Profile and assessment links, with a visible reminder that estimates do not guarantee placement.

### Mentor

1. Support queue with trigger reason, data recency, and suggested follow-up.
2. Assigned-student roster with search and cohort filters.
3. Student detail with evidence, goals, completed work, and coaching history.
4. Notes marked clearly as private or student-visible.
5. Cohort needs and follow-up workload, without ranking mentors by student scores alone.

### Admin/placement

1. Aggregate metrics with definitions, reporting period, and missing-data rate.
2. Placement stage counts and conversion, separated from predictions.
3. Cohort skill gaps and mentor coverage.
4. Data quality issues with ownership and remediation state.
5. Model version, evaluation sample, period, outcome definition, and limitations.
6. Access/audit/export controls and clear demo-data labeling.

## Interaction and responsive behavior

- Use compact, filterable desktop tables and preserve search, status, and primary actions on mobile.
- Confirm destructive actions; show success and failure feedback inline.
- Keep forms labeled, validated, and keyboard-operable; do not rely on placeholders as labels.
- Give useful empty states that explain how to get started.
- Avoid auto-refresh behavior that discards in-progress form edits.

### Sign-in campus image

The sign-in page uses `frontend/src/assets/lpu-campus-banner.webp`, provided by the user from https://lpu.distanceeducationschool.com/wp-content/uploads/2026/07/Mobile-banner-17.webp. Confirm the appropriate image and university logo usage rights before distributing or publishing the project.

The university seal used in the site header, sign-in page, session screen, and favicon is sourced from LPU's public profile at https://x.com/lpuuniversity. Check LPU's logo guidelines and authorization before publishing or distributing the project: https://www.lpu.in/LPUMedia/.
