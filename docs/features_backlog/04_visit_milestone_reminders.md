# Feature: Visit Milestone Reminders (10th, 50th, 100th)

## Background / Context
Mulai Gym is community-focused — members feel like the gym is a second home. We want to recognize loyal members at meaningful visit milestones (10, 50, 100 visits) so admins can congratulate them in person or via WhatsApp. This feature auto-generates reminders for those moments, reusing the existing `Reminder` system rather than building a parallel mechanism.

## Task Description
1. Pull latest changes for branch `main`.
2. Create new branch named `feat/visit_milestone_reminders`.
3. Implement the spec below.
4. Make sure unit tests are added and all tests pass.
5. Commit & push to the new branch.
6. Open a PR to `main`. In the PR, explain the feature context, the changes, and what testing was done locally.
7. Record a short video showing the reminder being generated and appearing in the admin and attach it to the PR.

## Spec
- Add a new `reminder_type` choice: `VISIT_MILESTONE` to the `Reminder` model. Update the model `choices`, run/add migration.
- Extend `reminders/management/commands/generate_reminders.py` to also generate `VISIT_MILESTONE` reminders:
  - For each active member, count their **completed visits** (visits with both `check_in_time` and `check_out_time`).
  - If their total visit count is exactly 10, 50, or 100 **and** their most recent visit's `check_in_time` was within the last 24 hours, create a reminder.
  - The `reason` field should be human-readable Indonesian, e.g. `"Selamat! Member sudah mencapai 10 kali check-in"` (replace 10 with 50 or 100 accordingly).
  - The `due_date` is the date of the milestone visit.
- Apply the existing `skip_auto_reminder` filter (members with `skip_auto_reminder=True` are excluded).
- Duplicate prevention: do not create a milestone reminder if one already exists for the same member with the same `reason`.
- **Auto-resolution**: milestone reminders auto-resolve once the admin clicks "Selesai" — no automatic resolution based on activity (different from PAYMENT_DUE / NO_VISIT). They are one-shot acknowledgments.

## Tests
- Test that a member with exactly 10 completed visits and a check-in within 24 hours gets a milestone reminder.
- Test the same for 50 and 100.
- Test that a member at 11, 49, 51, 99, 101 visits does NOT get one.
- Test that members with `skip_auto_reminder=True` are excluded.
- Test that running the command twice on the same day does not create duplicate milestone reminders.
- Test that members with only check-ins (no check-out) are not counted as completed visits.
- Update any existing reminder command tests that assert on `reminder_type` choices.
