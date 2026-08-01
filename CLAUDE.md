# Mulai Gym

Django app running mulaigym.id, the site and admin system for Mulai Gym in Bandung. A gym built for people who have never trained before: roughly 80% of members are first-timers, about half take classes, and the community feel between members and staff is the product's real asset. Keep that in mind when writing copy or designing a screen.

`README.md` documents **what the system does** (per-feature behaviour, business rules, admin workflows, infra). This file documents **how to work in it**. When you add a feature, put the behaviour in the README and any new convention or trap here.

## Stack

- **Framework**: Django 4.2 (server-rendered templates, no SPA, no JS build step)
- **Python**: 3.13, venv at `.venv/`
- **Database**: PostgreSQL (Supabase in production, local Docker Postgres for dev)
- **Frontend**: Bootstrap 5.3 + Font Awesome 6.4 from CDN, one hand-written `static/css/style.css`, vanilla JS inline in templates. Chart.js from CDN where a chart is needed.
- **Static files**: WhiteNoise
- **Hosting**: Docker on a DigitalOcean droplet, Nginx in front, Cloudflare for DNS/SSL, deploy via `.github/workflows/deploy.yml`
- **Cron on the droplet**: `generate_daily_class_instances.sh`, `generate_daily_reminders.sh`

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
- **Dates**: `{{ value|date:"d M Y" }}`. Month names in Indonesian only where a heading carries the date (see `MONTHS_ID` in `accounts/views.py`, `indonesian_day` in `classes/templatetags/class_extras.py`).
- **Timezone**: `USE_TZ=True`, `TIME_ZONE="Asia/Jakarta"`. Always `localtime()` a `DateTimeField` before taking `.date()`, or a late-evening visit lands on the wrong day.

### Templates

- All templates live in the project-level `templates/`, not in app directories.
- Member pages extend `base.html`; admin pages extend the admin base.
- **The class list has 4 near-identical card variants** (Ramadan light / Kelas Pemula / Semi Private / other). Anything that goes on a card belongs in a partial (`templates/classes/_booking_actions.html`, `_class_capacity.html`) and is `{% include %}`d, never copied 4 times.
- **Bump the CSS cache-buster** in `base.html` (`style.css?v=NN`) whenever you touch `static/css/style.css`, or members keep the old file for a year (`WHITENOISE_MAX_AGE`).
- **A wrong `{% static %}` path is a 500, not a broken image.** Production uses `CompressedManifestStaticFilesStorage`, which raises on a file that is not in the manifest. Anywhere a static path comes from data or config rather than being written inline, check it resolves with `staticfiles.finders.find()` and skip it if it does not, and add a test that walks the configured paths.
- **There is nothing serving `/media/`.** `MEDIA_URL` and `MEDIA_ROOT` are set, but `urls.py` only serves static and WhiteNoise does not cover media, so no model has ever used an `ImageField`. Anything upload-shaped needs an Nginx location block on the droplet first. Until then, images ship in `static/` with the deploy.

### Views

- **Precompute per-row state in the view, not in the template.** A template calling `instance.booked_members.count()` or `member in instance.booked_members.all` runs a query per card. Attach plain attributes to each object in `get_context_data` instead (see `ClassListView`), and pin the result with `assertNumQueries` so it cannot regress. The class list stays at 6 queries whether it renders 6 cards or 12.
- **One rule, one function.** A rule that both a template and a POST handler need lives in one place, so a member never sees a button the server then refuses. `booking_block_reason()` in `classes/models.py` is the pattern: it returns `None` or a dict with `code` / `short` / `label` / `message`, and the class list, the class detail page and `book_class` all call it.
- **Business limits are module constants**, not magic numbers: `MAX_CLASSES_PER_DAY` (`classes/models.py`), `RECENT_VISITS_LIMIT` / `PAST_CLASSES_LIMIT` / `NUDGE_DAYS_BEFORE` (`accounts/views.py`). User-facing copy interpolates the constant so the number never drifts from the rule.
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

## Deploy

`deploy.yml` (drone-ssh onto the droplet) stops the old container, starts the new one, migrates, runs `collectstatic`, then waits for health.

- **The container health check is `curl -f http://localhost:8000/`, i.e. the homepage.** So the homepage is the liveness probe: if it errors, the deploy fails and the container is marked unhealthy. Keep that page cheap and hard to break.
- **The new container serves traffic before migrations finish.** There is no blue/green step, so every release has a short window of new code against the old schema. A page that reads a table added in the same release must degrade rather than raise in that window (see `_homepage_reviews()` in `accounts/views.py`). Migrations run before the health gate, so a schema-adding release deploys, but real visitors can still land inside the window.
- A failed deploy leaves the **new** container running, because the old one is removed before the new one is started. Recovery is usually `docker exec mulai_web python manage.py migrate` on the droplet, not a rollback.

## Verifying work

Tests are not enough for a member-facing change: look at the page.

- Run the app and drive it. Chrome headless over the DevTools Protocol works well for this (navigate, log in, click the real button, screenshot at 390px mobile).
- **Restart `runserver` after editing a template if you started it with `--noreload`** — Django caches compiled templates for the process lifetime, so you will screenshot the old markup.
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
