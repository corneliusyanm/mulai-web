# Feature: Equipment Popularity Report

## Background / Context
We track equipment guide views (total, authenticated, anonymous) but never look at the data analytically. We want to know which equipment guides drive engagement so the content team knows what kind of videos to make next. This feature surfaces that data in a dedicated report page.

## Task Description
1. Pull latest changes for branch `main`.
2. Create new branch named `feat/equipment_popularity_report`.
3. Implement the spec below.
4. Make sure unit tests are added and all tests pass.
5. Commit & push to the new branch.
6. Open a PR to `main`. In the PR, explain the feature context, the changes, and what testing was done locally.
7. Record a short video walking through the page and attach it to the PR.

## Spec
- New admin page at `/admin/analytics/equipment-popularity/`, registered under the existing Analytics section.
- The page lists all `Equipment` records ranked by `total_views` descending.
- Required to add a new model field: `weekly_views_snapshot` (JSONField, default `{}`) on `Equipment`. Stores `{ "YYYY-MM-DD": total_views_at_that_date }` as a snapshot taken at end of each ISO week. Add migration.
- Add a daily management command `equipment/management/commands/snapshot_equipment_views.py` that, on Sundays, writes the current `total_views` to `weekly_views_snapshot` keyed by today's date. Idempotent on the same day.
- Document the cron schedule in the README's Equipment section, mirroring the style of `generate_class_instances`.
- Table columns: Equipment name (linked to public detail page), Muscle group, Total views, Authenticated views, Anonymous views, Member engagement % (authenticated / total), This week's views, Last week's views, Week-over-week change (signed %).
- "This week's views" = current `total_views` minus the most recent Sunday snapshot (or 0 if no snapshot).
- "Last week's views" = the diff between the two most recent snapshots.
- Above the table, show summary: total view count across all equipment, total members engaged this week (sum of authenticated views this week), top muscle group by views.

## Tests
- Test the snapshot command writes the current `total_views` keyed by today on Sundays.
- Test the snapshot command is idempotent on the same day (same key overwritten, no duplicate).
- Test the WoW calculation against a fixture with two snapshots.
- Test the engagement % calculation, including the divide-by-zero case (total_views = 0 → 0%).
- Test that equipment with zero views still appears in the list (at the bottom).
- Test that the page requires `is_staff` permission.
