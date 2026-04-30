# Feature: Churn Reason Tracker

## Background / Context
Members leave for many reasons — moved jobs, moved city, moved house, lost interest, etc. Right now we lose this signal entirely. Without it, we can't tell whether churn is something we can fix (e.g. lost interest, found another gym) or something we can't (e.g. moved cities). This feature captures the reason at the point of non-renewal, then aggregates the data weekly.

## Task Description
1. Pull latest changes for branch `main`.
2. Create new branch named `feat/churn_reason_tracker`.
3. Implement the spec below.
4. Make sure unit tests are added and all tests pass.
5. Commit & push to the new branch.
6. Open a PR to `main`. In the PR, explain the feature context, the changes, and what testing was done locally.
7. Record a short video walking through the field, the form, and the breakdown section, and attach it to the PR.

## Spec

### Model changes
- Add two fields to `Member`:
  - `churn_reason`: CharField with choices: `MOVED_JOB`, `MOVED_CITY`, `MOVED_HOUSE`, `LOST_INTEREST`, `TOO_EXPENSIVE`, `FOUND_OTHER_GYM`, `HEALTH_ISSUE`, `OTHER`. Nullable, blank=True.
  - `churn_reason_notes`: TextField, blank=True. Free-text field for OTHER or extra context.
- Add migration.

### Admin changes
- In `MemberAdmin`, expose both fields in the edit form.
- Add a list filter on `churn_reason` so admins can quickly slice by reason.

### Weekly Metrics section
- In the Weekly Metrics Tracker page (`/admin/analytics/weekly-metrics`), add a new section called **"Churn Reasons"**.
- A member is counted as "churned this week" if their `active_until` falls inside the `start_date`–`end_date` filter range AND they have **no payment** with `payment_date > active_until` (i.e. they did not renew). Reuse logic from the existing "Did Not Repurchase" section if practical.
- Aggregate `churn_reason` across these churned members:
  - Reason label (use the human-readable display, e.g. "Pindah kerja"), Count, Percentage.
  - Members with `churn_reason = NULL` are grouped under "(Belum diisi)".
- Sort rows by count descending.

## Tests
- Test the new fields default to null/blank on existing members.
- Test the admin form accepts and saves both fields.
- Test the breakdown section correctly counts churned members by reason for a fixture spanning multiple weeks.
- Test that members who renewed (have a payment after `active_until`) are NOT counted as churned.
- Test that members with `churn_reason = NULL` appear under "(Belum diisi)".
- Test that the section ignores members whose `active_until` falls outside the date range.
- Test that the page still requires `is_staff` permission.
