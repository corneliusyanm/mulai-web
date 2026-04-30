# Feature: Class No-Show Tracker

## Background / Context
Members book classes (Kelas Pemula, Semi Private) but sometimes don't actually show up. Right now there's no easy way to see who booked but didn't check in — which means we can't follow up, and we can't tell if class capacity is being wasted. This feature gives admins a single page to see no-shows over a date range.

## Task Description
1. Pull latest changes for branch `main`.
2. Create new branch named `feat/class_no_show_tracker`.
3. Implement the spec below.
4. Make sure unit tests are added and all tests pass.
5. Commit & push to the new branch.
6. Open a PR to `main`. In the PR, explain the feature context, the changes, and what testing was done locally.
7. Record a short video walking through the page and attach it to the PR.

## Spec
- New admin page at `/admin/analytics/class-no-shows/`, registered under the existing Analytics section (same pattern as `weekly-metrics`).
- Page has a date range filter (`start_date`, `end_date`), defaulting to the current week (Mon–Sun).
- The page lists all `ClassBooking` records where:
  - The booking status is **confirmed/booked** (not cancelled, not on waitlist).
  - The associated `ClassInstance` falls inside the date range.
  - The member has **no `Visit`** with `check_in_time` on the same date as the class instance.
- For each no-show row, show: Class name, Class date, Class start time, Member name, Phone (with WhatsApp link, same pattern as other admin sections), Member's total no-show count in the selected range.
- Sort rows by class date descending, then class start time.
- Above the table, show summary stats: total no-shows in range, unique members who no-showed, no-show rate (% of confirmed bookings in range that became no-shows).
- Add a "Download CSV" button matching the existing CSV export pattern (e.g. `MemberAdmin`).

## Tests
- Test that a booking with no matching visit on the class date is counted as a no-show.
- Test that a booking with a visit on the same date is **not** counted (member showed up).
- Test that cancelled bookings and waitlist entries are excluded.
- Test that bookings outside the date range are excluded.
- Test the no-show rate calculation against a known fixture.
- Test the CSV export contains the expected columns and rows.
- Test that the page requires `is_staff` permission.
