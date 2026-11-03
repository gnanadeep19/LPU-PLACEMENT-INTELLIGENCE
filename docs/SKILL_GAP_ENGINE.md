# Skill-gap and recommendation engine

The readiness response contains one structured gap record for each supported
feature, including certifications. Each record includes:

- Current and target values
- Remaining `gap_delta`
- `target_met`
- Severity and normalized priority
- A measurable action

Targets are read from the model artifact's `target_thresholds` metadata, with
the documented institutional defaults used for legacy artifacts. This keeps
the gap engine aligned with the model configuration instead of duplicating
thresholds in the frontend.

Recommendations include `target_feature` and `measurable` metadata so clients
can connect an action to a specific gap. Recommendations are guidance only;
they do not replace company-specific eligibility rules or guarantee placement.
