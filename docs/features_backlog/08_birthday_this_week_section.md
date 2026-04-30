# Feature: Birthday This Week Section

## Background / Context
Mulai Gym is community-focused — wishing members happy birthday is a simple, high-leverage way to make people feel at home. Right now we have no way to know whose birthday is coming up. This feature adds a birthdate field to members and surfaces birthdays in the weekly metrics page so admins can send wishes via WhatsApp.

**Important:** Birthdate must be **optional** during member signup and editing. We don't want to force people to provide it — adoption will be gradual.

## Task Description
1. Pull latest changes for branch `main`.
2. Create new branch named `feat/birthday_this_week_section`.
3. Implement the spec below.
4. Make sure unit tests are added and all tests pass.
5. Commit & push to the new branch.
6. Open a PR to `main`. In the PR, explain the feature context, the changes, and what testing was done locally.
7. Record a short video walking through the optional field on signup, the admin editor, and the new section, and attach it to the PR.

## Spec

### Model changes
- Add `birthdate` to `Member`: `DateField(null=True, blank=True)`. Add migration.

### Form changes
- `MemberSignUpForm` and `MemberEditForm` (`accounts/forms.py`): expose `birthdate` as an **optional** field. Use a `DateInput` widget with `type="date"` so mobile browsers show a native date picker.
- Templates `signup.html` and `member_edit.html`: render the new field with a clear label, e.g. "Tanggal Lahir (opsional)". The form must validate and save successfully when the field is left blank.

### Admin changes
- Expose `birthdate` in `MemberAdmin` edit form.
- Add it to the CSV export columns for both "Download All Members CSV" and "Download Active Members CSV".

### Weekly Metrics section
- In the Weekly Metrics Tracker page (`/admin/analytics/weekly-metrics`), add a new section called **"Ulang Tahun Minggu Ini"**.
- Lists members whose `birthdate` (month + day, ignoring year) falls inside the selected `start_date`–`end_date` range.
- Handle Feb 29 by treating Feb 28 as a match in non-leap years (so leap-year-born members still get wished).
- Columns: Member name (linked to admin detail), Phone (WhatsApp link), Birthdate (formatted as "DD MMM"), Age turning (computed from birthdate year), `is_pemula` flag.
- Sort by birthdate ascending within the range.
- Members without a birthdate are silently excluded — do not show "(Belum diisi)" rows here.

## Tests
- Test that signup succeeds when `birthdate` is omitted.
- Test that signup succeeds when `birthdate` is provided.
- Test that the edit form accepts a blank `birthdate`.
- Test the section includes a member whose birthday falls inside the range.
- Test the section excludes a member whose birthday is outside the range.
- Test that members without a birthdate are excluded.
- Test the Feb 29 fallback to Feb 28 in non-leap years.
- Test the CSV export contains the `birthdate` column.
- Test that the page still requires `is_staff` permission.
