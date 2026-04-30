# Feature: Referral Source Breakdown

## Background / Context
We collect `know_mulai_gym_from` during member signup, but we never look at the data in aggregate. We don't actually know which marketing channels are bringing members in. This feature surfaces that data so we can decide where to invest marketing effort.

## Task Description
1. Pull latest changes for branch `main`.
2. Create new branch named `feat/referral_source_breakdown`.
3. Implement the spec below.
4. Make sure unit tests are added and all tests pass.
5. Commit & push to the new branch.
6. Open a PR to `main`. In the PR, explain the feature context, the changes, and what testing was done locally.
7. Record a short video of the new section and attach it to the PR.

## Spec
- In the Weekly Metrics Tracker page (`/admin/analytics/weekly-metrics`), add a new section called **"Referral Source Breakdown"**. Use the "All Weekly Payments" / "New Members" sections as a reference for layout and styling.
- The section aggregates the `know_mulai_gym_from` field across **new members** in the selected `start_date` to `end_date` range. Reuse the same "New Member" definition from `feat/weekly_add_new_member_section` (first non-`*-0` package payment falls inside the range).
- For each unique source value, show:
  - Source label (the raw `know_mulai_gym_from` text — keep as-is, do not normalize)
  - Count of new members with that source
  - Percentage of total new members in the range
- Sort rows by count descending.
- If `know_mulai_gym_from` is empty/null, group those under a row labeled "(Tidak diisi)".
- Below the table, show a single summary line: total new members in range, total unique sources.

## Tests
- One test asserting counts are correct given a fixture of new members with mixed source values.
- One test asserting empty/null sources are grouped under "(Tidak diisi)".
- One test asserting the section ignores members whose first qualifying payment falls outside the date range.
- One test asserting percentages sum to 100 (within rounding tolerance).
