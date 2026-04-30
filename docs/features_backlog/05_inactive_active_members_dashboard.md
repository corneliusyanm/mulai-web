# Feature: Inactive Active-Members Dashboard

## Background / Context
We have members who paid for memberships but stopped showing up. The current Smart Alerts panel hints at this, but there's no full sortable view. This feature gives admins a dedicated dashboard to identify and follow up with paying-but-not-visiting members — a key churn-prevention lever.

## Task Description
1. Pull latest changes for branch `main`.
2. Create new branch named `feat/inactive_members_dashboard`.
3. Implement the spec below.
4. Make sure unit tests are added and all tests pass.
5. Commit & push to the new branch.
6. Open a PR to `main`. In the PR, explain the feature context, the changes, and what testing was done locally.
7. Record a short video walking through the page and attach it to the PR.

## Spec
- New admin page at `/admin/analytics/inactive-members/`, registered under the existing Analytics section.
- Lists members where:
  - `active_until >= today` (still paying members).
  - Either no visit ever, or last visit was more than 14 days ago.
- Three filter buttons at the top: **14+ days**, **30+ days**, **60+ days**. Default is 14+. Tap to filter; tap again to clear (same UX pattern as the class list filters).
- Table columns: Member name (linked to admin detail), Phone (WhatsApp link), Last visit date (or "Belum pernah"), Days since last visit, `active_until`, Days remaining on membership, `is_pemula` flag.
- Sort by **days since last visit** descending. Members who never visited go to the top (treat as infinity).
- Above the table, show summary: total inactive members, average days since last visit, number who never visited.
- Add a "Download CSV" button matching the existing CSV export pattern.

## Tests
- Test that a member with `active_until` in the past is excluded.
- Test that a member who visited yesterday is excluded.
- Test that a member who visited 15 days ago appears in the 14+ filter but not the 30+ filter.
- Test that a member who never visited appears at the top of the list.
- Test sort order is correct.
- Test the CSV export contains the expected columns and rows.
- Test that the page requires `is_staff` permission.
