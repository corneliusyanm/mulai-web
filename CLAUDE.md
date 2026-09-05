# Mulai Gym

Django app running mulaigym.id, the site and admin system for Mulai Gym in Bandung. A gym built for people who have never trained before: roughly 80% of members are first-timers, about half take classes, and the community feel between members and staff is the product's real asset. Keep that in mind when writing copy or designing a screen.

`README.md` documents **what the system does** (per-feature behaviour, business rules, admin workflows, infra). This file documents **how to work in it**. When you add a feature, put the behaviour in the README and any new convention or trap here.

## Stack

- **Framework**: Django 4.2 (server-rendered templates, no SPA, no JS build step)
- **Python**: 3.13, venv at `.venv/`
- **Database**: PostgreSQL (Supabase in production, local Docker Postgres for dev)
- **Frontend**: Bootstrap 5.3 + Font Awesome 6.4 from CDN, one hand-written `static/css/style.css`, page-specific vanilla JS inline in templates, plus one shared `static/js/mulai.js` for motion helpers. Chart.js from CDN where a chart is needed.
- **Static files**: WhiteNoise
- **Hosting**: Docker on a DigitalOcean droplet, Nginx in front, Cloudflare for DNS/SSL, deploy via `.github/workflows/deploy.yml`
- **Cron on the droplet**: `generate_daily_class_instances.sh`, `generate_daily_reminders.sh` (both ~07:03 WIB), `generate_daily_penalties.sh` (21:00 WIB, after closing)

## Apps

| App | Models | What it owns |
| --- | --- | --- |
| `accounts` | `Member`, `User`, `ActiveMember` (proxy), `Tamu`, `Masukkan`, `Prospect` | Members, signup/login, `/akun`, guest book, feedback |
| `visits` | `Visit` | Check-in/out, **and the custom admin site + all analytics dashboards** |
| `classes` | `Class`, `ClassSchedule`, `ClassInstance` | Class schedule, booking, waitlist |
| `payments` | `Package`, `Payment` | Memberships; `Package.code` drives everything |
| `purchases` | `Product`, `Sale`, `SaleItem` | Store sales |
| `reminders` | `Reminder` | Staff follow-up queue, auto-generated daily |
| `equipment` | `Equipment` | Panduan Alat guides + view analytics |
| `announcements` | `Announcement` | Site-wide banner |
| `homepage` | `ReviewSummary`, `Testimonial` | Curated Google reviews shown on the homepage |
| `nutrition` | `ChapterProgress`, `QuizAnswer`, `DailyQuestion`, `DailyAnswer` | Belajar Gizi chapters at `/gizi/` (content in `content.py`, not the DB) + Kuis Harian at `/gizi/harian/` (seeded into the DB) |
| `leaderboard` | none | Papan Peringkat at `/papan/`: points computed live from visits, classes and quizzes, cached, no tables |
| `grand_opening` | `GrandOpeningRegistration` | One-off launch event |

## Commands

```bash
python manage.py runserver              # dev server (reads .env)
python manage.py test                   # full suite, needs Postgres (see Testing)
python manage.py test accounts classes  # one or more apps
python manage.py migrate
python manage.py generate_class_instances [days]   # default 3
python manage.py generate_reminders [--dry-run]
docker compose up -d                    # local Postgres + app
```

## Conventions

### Members are not Django users

`Member` has no relation to `django.contrib.auth`. A member is "logged in" when `request.session["member_email"]` is set (1-year session). Gate member pages with `MemberRequiredMixin` (class views) or `@member_login_required` (function views), both in `accounts/views.py` / `classes/views.py`. `User` / `is_staff` is only for admin staff.

### Language

User-facing copy is **Indonesian**, informal and warm ("Kamu", "Yuk", "biar nggak putus"). Code, comments, commit messages, docstrings and test names are **English**. Never machine-translate copy: write it the way the admins would say it to a member.

### Formatting in templates

- **Money**: `Rp {{ amount|floatformat:0|intcomma }}` (needs `{% load humanize %}`), or `f"Rp {value:,.0f}"` in Python. Comma separators, matching the rest of the codebase.
- **Dates a member reads are Indonesian, always.** `{% load id_dates %}` then one of four filters, shortest that still answers the question: `indonesian_day` ("Minggu, 30 Agustus 2026", a heading that *is* the date), `indonesian_date` ("Minggu, 30 Agu", a date inside a sentence), `indonesian_full_date` ("30 Agu 2026", a row in a list), `indonesian_day_month` ("30 Agu", a bracket after a time). The words live in `accounts/dates.py`, a leaf module with no imports so nothing can cycle through it; the filters in `accounts/templatetags/id_dates.py` are thin wrappers, and Python code (messages, WhatsApp invites) calls `accounts.dates` directly. **Never `|date:"d M Y"` on a member page**: it renders "29 Oct 2026", and four of twelve month abbreviations plus every weekday differ from Indonesian, so it looks right in eight months of the year and wrong in the other four. Admin pages are the exception and still use the Django filter.
- **Timezone**: `USE_TZ=True`, `TIME_ZONE="Asia/Jakarta"`. Never `.date()` a datetime straight: use `timezone.localdate()` for today and `timezone.localdate(value)` for a stored `DateTimeField`. Jakarta is UTC+7, so from 00:00 to 07:00 local the UTC date is still yesterday. That window is the only time the two spellings disagree, which is why a UTC `.date()` can sit there for years looking fine. ORM `__date` lookups already convert to Asia/Jakarta, so a raw `.date()` on the Python side silently compares two different days.
- **The daily crons fire at 07:03 WIB**, i.e. 00:03 UTC, measured from 342 days of `visits_reminder.created_date`, not the "6 AM" the README example shows. That is three minutes clear of the UTC date boundary: anything scheduled earlier lands in the window above and computes yesterday. Confirm with `crontab -l` on the droplet before trusting any number here.

### Templates

- All templates live in the project-level `templates/`, not in app directories.
- Member pages extend `base.html`; admin pages extend the admin base.
- **The class list has 4 near-identical card variants** (Ramadan light / Kelas Pemula / Semi Private / other). Anything that goes on a card belongs in a partial (`templates/classes/_booking_actions.html`, `_class_capacity.html`) and is `{% include %}`d, never copied 4 times.
- **Bump the CSS cache-buster** in `base.html` (`style.css?v=NN`) whenever you touch `static/css/style.css`, or members keep the old file for a year (`WHITENOISE_MAX_AGE`). Same for `js/mulai.js?v=N`.
- **Animating a width from zero needs the transition off first.** `el.style.width = 0` does not jump to zero when width has a transition, it animates *towards* zero, and the target set right after overrides it from wherever it got to: nothing moves. Set the start value with `transition: none`, flush with `void el.offsetWidth`, restore, then set the target (`mgGrow` in `static/js/mulai.js`). This shipped broken once. Sample the frames before believing a bar animates.
- **Motion is opt-in from the markup.** `static/js/mulai.js` reads `data-count-up`, `data-grow` and `data-ring`. Everything it touches must render complete and correct without it: nothing in it hides content. One `mgRise` keyframe for the whole site, and every effect is off under `prefers-reduced-motion`.
- **Do not add reveal-on-scroll.** It was built and removed: cards that fade in as you scroll read as a page still loading, and withholding content that is ready feels slower than showing it. An on-load stagger that finishes inside a second (the Belajar Gizi chapter list, the leaderboard rows) is fine.
- **A wrong `{% static %}` path is a 500, not a broken image.** Production uses `CompressedManifestStaticFilesStorage`, which raises on a file that is not in the manifest. Anywhere a static path comes from data or config rather than being written inline, check it resolves with `staticfiles.finders.find()` and skip it if it does not, and add a test that walks the configured paths.
- **`position: sticky` does not stick anywhere on this site.** `body` carries `overflow-x: hidden` (`static/css/style.css`), which makes body a scroll container, so a sticky child resolves against the body box, which is as tall as the page, and never pins. It fails silently: the element just scrolls away. Repeat the header, or reach for something else.
- **`btn-primary` is invisible outside a white card**, since it is the same purple as the page background. On the purple, use `btn-secondary` (lime). Same trap for text: `body` sets white type, so anything inside a white card must name its own colour or it disappears.
- **Hand-written multiple choice drifts to the middle answer.** Authored by hand, 77 of 100 daily questions had the answer at B and none at C. Any new question set goes through `place_answer()` in `nutrition/shuffle.py`, and a test asserts no letter takes more than half.
- **No emoji in body copy.** They read as machine-written, and that is the wrong impression for anything a member has to trust. Emoji are fine as icons in a list or a tile, where they replace an image; not inside sentences, headings, or explanations.
- **A rule the member has to compute is a rule they will break.** Times in class copy are printed as clock times the server worked out ("batalin sebelum jam 13:15", "Bisa jam 16:15"), never as offsets ("4 jam sebelum"). Roughly 80% of members are first-timers and a good number find rules tiring; the ones most likely to be caught by a deadline are the least likely to work it out. The rule also has to appear on the surface where the action happens (the card, the account row, the confirm box), not only on the guide page, which is the backup for the ones who ask.
- **Anywhere a member can act, they can be told.** `/akun` rendered no Django messages for years, which was harmless until cancelling from that page could cost a strike, and then the one message that mattered vanished. Before adding an action to a page, check the page renders `{% if messages %}`.
- **A template reading a field that does not exist fails silently.** Django resolves a missing attribute to the empty string, so the page renders with a hole in it and nothing in the logs. The payment rows on `/akun` printed a blank line for months from `payment.duration_choice`, a field `Payment` has never had. If a row looks empty, check the field is real before styling around it, and pin the value with a test.
- **There is nothing serving `/media/`.** `MEDIA_URL` and `MEDIA_ROOT` are set, but `urls.py` only serves static and WhiteNoise does not cover media, so no model has ever used an `ImageField`. Anything upload-shaped needs an Nginx location block on the droplet first. Until then, images ship in `static/` with the deploy.

### Views

- **Precompute per-row state in the view, not in the template.** A template calling `instance.booked_members.count()` or `member in instance.booked_members.all` runs a query per card. Attach plain attributes to each object in `get_context_data` instead (see `ClassListView`), and pin the result with `assertNumQueries` so it cannot regress. The class list stays at 6 queries whether it renders 6 cards or 12.
- **One rule, one function.** A rule that both a template and a POST handler need lives in one place, so a member never sees a button the server then refuses. `booking_block_reason()` in `classes/models.py` is the pattern: it returns `None` or a dict with `code` / `short` / `label` / `message`, and the class list, the class detail page and `book_class` all call it.
- **One exception to constants-in-code**: every tunable number in the class rules lives in the `PenaltySettings` row editable at `/admin` (`advance_classes_per_day`, `extra_booking_minutes`, `late_cancel_hours`, `window_days`, `misses_allowed`, `ban_days`), because they are being tuned against real behaviour and a deploy per experiment is the wrong friction. Everything else stays a constant.
- **Pass the settings row down, do not fetch it per card.** `booking_block_reason()` takes `now` and `settings`, and `ClassListView` resolves both once for the page. Fetching the row inside the function would put a query on every card and quietly undo the whole point of that view. `assertNumQueries(8)` in `ListPageBookingTest` is what stops it coming back.
- **Business limits are module constants**, not magic numbers: `RECENT_VISITS_LIMIT` / `PAST_CLASSES_LIMIT` / `NUDGE_DAYS_BEFORE` (`accounts/views.py`). User-facing copy interpolates the constant so the number never drifts from the rule.
- **Member-facing rules go in the view, not the model**, so staff can still override from `/admin` (e.g. an admin can add a member to a 3rd class in a day).
- Only accept a fixed set of values for redirect targets (`next=list`), never an arbitrary URL.

### Admin

The custom admin site is `admin_site` in `visits/admin.py`, and much of the model admin registration lives in `visits/admin_init.py` rather than each app's `admin.py`. The analytics dashboards are custom views hung off that site. Some of those views use **raw Postgres SQL** (`extract(... from ...)`, `date_trunc`, `INTERVAL`).

## Testing

- `python manage.py test`, Django `TestCase`, one test class per behaviour, appended to the app's `tests.py`. No pytest.
- **Postgres is required.** Running the suite on SQLite fails ~12 analytics tests because of the raw SQL above. Those failures are not real.
- Test names read as sentences describing the behaviour (`test_waitlist_promotion_still_works_at_the_limit`), not `test_1`.
- Cover the boundaries, not just the happy path: the day before / of / after an expiry, an empty list, a member with no membership, a cancelled class.
- Watch out for **date-relative assumptions**. `timedelta(days=1)` can cross a month boundary and break a "this month" assertion. Anchor such tests to values that cannot straddle the boundary.
- `Visit.check_in_time` is `auto_now_add`, so passing it to `create()` is silently ignored. Set it with `Visit.objects.filter(pk=...).update(check_in_time=...)`.
- **A class instance dated "today" makes a test depend on the hour it runs.** Booking now refuses a class that has already started, so a fixture at 09:00 today passes all morning and fails all afternoon. Date fixtures tomorrow, or build them from `timezone.now() + timedelta(...)` and take the date *and* time from the same moment so a run at 23:50 does not produce a class in the past.

## Deploy

`deploy.yml` (drone-ssh onto the droplet) stops the old container, starts the new one, migrates, runs `collectstatic`, then waits for health.

- **The container health check is `curl -f http://localhost:8000/`, i.e. the homepage.** So the homepage is the liveness probe: if it errors, the deploy fails and the container is marked unhealthy. Keep that page cheap and hard to break.
- **The new container serves traffic before migrations finish.** There is no blue/green step, so every release has a short window of new code against the old schema. A page that reads a table added in the same release must degrade rather than raise in that window (see `_homepage_reviews()` in `accounts/views.py`). Migrations run before the health gate, so a schema-adding release deploys, but real visitors can still land inside the window.
- A failed deploy leaves the **new** container running, because the old one is removed before the new one is started. Recovery is usually `docker exec mulai_web python manage.py migrate` on the droplet, not a rollback.

## Verifying work

Tests are not enough for a member-facing change: look at the page.

- Run the app and drive it. Chrome headless over the DevTools Protocol works well for this (navigate, log in, click the real button, screenshot at 390px mobile).
- **Restart `runserver` after every template edit.** `DEBUG` comes from `DJANGO_DEBUG` and defaults to False, and with DEBUG off Django wraps the template loaders in `cached.Loader`, which holds the compiled template for the process lifetime. The autoreloader only watches `.py`, so a template edit alone never restarts it and you screenshot the old markup while the file on disk is right. Probe the DOM before believing a change "did not work".
- Full-page screenshots (`captureBeyondViewport`) resize the viewport and can catch a Chart.js re-render mid-animation, which looks like a chart with no bars. Read the chart's real geometry before believing a screenshot.
- Chrome clamps very small window sizes on macOS, so a "clipped" narrow screenshot is usually the harness, not the CSS. Confirm with `document.documentElement.scrollWidth === window.innerWidth`.

## Data safety

- The local Postgres on port **5435** holds a copy of production: ~800 real members with real phone numbers. **Read from it freely, never write content to it.** No test members, no test bookings, no fake payments.
- **Migrations are the exception: apply them locally as soon as you add one** (`python manage.py migrate`). They are the same additive schema change the deploy will run, not test data. The test suite builds its own database, so a green suite says nothing about whether the dev database is up to date, and the first page load after adding a model will 500 with `relation ... does not exist`.
- **After adding a model, load the affected page against the real local database**, not only a throwaway one. That is what catches an unapplied migration, a missing table, and anything that depends on production-shaped data.
- Querying it for design decisions is encouraged and has already changed decisions (for example: the Silver and Gold add-ons have never expired on a different day from the gym membership, so the expiry nudge only checks `active_until`).
- For anything that needs writes, use a throwaway SQLite or a scratch database, seeded by a script.
- The Supabase MCP tools are available for schema questions and read-only queries on production. Do not apply migrations or edge functions through them without being asked.

## Working style

- **Ask before building when a choice would change the result.** Confirm the ambiguous decisions up front, in one batch, then implement the whole thing. Do not stop mid-way to ask about something you could have asked at the start.
- **Never use em-dashes**, in code, comments, commit messages, docs, or replies. Commas, colons or separate sentences instead.
- Prefer plain words over fancy ones, in replies and in user-facing copy.
- Report honestly. If something is unverified, say so. If a test failed, show it.
- **Commits**: several small ones over one big one, each with its own tests, and a message that explains *why* the change exists, not just what changed. **Never push.** The user reviews locally first.
- Say what you left out and why, rather than quietly widening or narrowing the task.
