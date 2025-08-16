# Mulai Gym Web App

It's a Django project, for Gym Management System. The Gym name is called Mulai Gym. It's in Bandung, Indonesia. It's a gym focused for Newbies. Our goal is to be the best gym for newbie in Bandung, so when anyone in Bandung wants to start the habit of going to the gym, they will choose us.
https://www.instagram.com/mulaigym.id
https://mulaigym.id

## Infrastructure & Deployment

### DNS & SSL Setup
- **Domain**: mulaigym.id (registered with Niagahoster/Hostinger)
- **DNS**: Cloudflare nameservers (`bruce.ns.cloudflare.com`, `janet.ns.cloudflare.com`)
- **SSL**: Let's Encrypt certificates via Cloudflare DNS challenge
- **Server**: DigitalOcean Droplet (178.128.116.170)
- **Proxy**: Cloudflare (proxied A record)

### SSL Certificate Management
- **Provider**: Let's Encrypt (90-day certificates)
- **Method**: Cloudflare DNS challenge (supports wildcards)
- **Auto-renewal**: Cron job runs daily at 3 AM
- **Domains**: `mulaigym.id` and `*.mulaigym.id`

## Visits & Check-in/Out

### Session
- 1-year duration
- Key: `member_email` (Used even when logging in/checking in via phone number)
- Persists across check-in/out

### Models
- **`Visit` (`visits/models.py`)**
  - `member`: ForeignKey (Member)
  - `check_in_time`: DateTimeField
  - `check_out_time`: DateTimeField (nullable)
- **`Member` (`accounts/models.py`)**
  - `phone_number`: CharField (Unique, stores digits only, e.g., 628123...)
  - `active_until`: DateTimeField (nullable)
  - `is_active_member` property: Checks if `active_until >= today`.

### Admin (`visits/admin_init.py`)
- **`MemberAdmin`**
  - Displays name, email, phone, `active_until`, status.
  - `membership_status` method calculates Active/Expired.
- **`VisitAdmin` (`visits/admin.py`)**
  - Displays member, check-in/out times, duration.
  - Filters, search fields defined.

### Views (`visits/views.py`)
- **`check_in_page`** (`/check-in`)
  - This view handles both manual login via `POST` and automatic check-in for already logged-in users via `GET`.
  - For a `POST` request (user not logged in), it validates the member's email or phone number, creates a session, and then proceeds to the automatic check-in logic.
  - For a `GET` request (user is logged in), it idempotently checks the user in using `get_or_create`. This means a new `Visit` is only created if the member does not already have an active (not checked-out) visit.
  - If the member is inactive, it renders a failure page.
  - On a successful check-in (or if the member was already checked in), it redirects to `/check-in/success`.
- **`check_in_success`** (`/check-in/success`)
  - This view is purely for displaying the result of a check-in.
  - It fetches the member's most recent visit, regardless of whether they are still checked in or have already checked out.
  - This prevents redirect loops where a user with a completed visit would be sent away from the success page. It will only redirect to the main check-in page if the user is not logged in or has no visit history at all.
- **`check_out_page`** (`/check-out`)
  1. Checks session for `member_email` (renders fail if not logged in).
  2. Tries to find an active `Visit` for the member.
     - Finds latest active `Visit` for member.
     - Sets `check_out_time`, saves `Visit`.
     - Renders success/failure template.
- **`forget_member`** (`/forget-member`)
  - Clears `member_email` from session.

### Check-in/Out Flow Diagram
```mermaid
graph TD
    subgraph Check-in Process
        A[Visit /check-in] --> B{Logged In?}
        B -->|No| C[Show Email/Phone Form]
        C -->|POST| D{Find Member}
        D -->|Not Found| E[Show Error]
        D -->|Found| F[Log In User<br>(Create Session)]
        F --> G
        B -->|Yes| G{Member Active?}
        G -->|No| H[Show Failure: Inactive Member]
        G -->|Yes| I(Idempotent Check-in<br>get_or_create Visit)
        I --> J[Redirect to /check-in/success]
    end

    subgraph Success Page
        K[Visit /check-in/success] --> L{Logged In?}
        L -->|No| M[Redirect to /check-in]
        L -->|Yes| N[Find Latest Visit<br>(Active or Not)]
        N --> O[Show Success Page<br>quick_check_in.html]
    end

    subgraph Check-out Process
        P[Visit /check-out] --> Q{Logged In?}
        Q -->|No| R[Show Failure: Not Logged In]
        Q -->|Yes| S{Has Active Visit?}
        S -->|No| T[Show Failure: No Active Visit]
        S -->|Yes| U[Auto Check-out]
    end
```

### Validations & Messages
- Check-in:
  - Must provide Email or Phone Number on login.
  - Member must exist.
  - Must be active member (logged in even if check-in fails here).
  - No duplicate active visits (logged in even if check-in fails here).
  - Messages: "Already Checked In", "Membership Expired", "Member not found", "Please provide email or phone".
- Check-out:
  - Must be logged in
  - Must have active visit
  - Messages: "Not Logged In", "No Active Visit Found"

## Accounts

### URLs
The account-related pages are accessible at the following URLs:
- **Registration**: `/daftar/`
- **Login**: `/masuk/`
- **Logout**: `/keluar/`
- **Member Details**: `/akun/`
- **Edit Profile**: `/akun/edit/`

### Forms (`accounts/forms.py`)
- **`MemberSignUpForm`, `MemberEditForm`**: Include `country_code` (default +62) and `phone_number_display` fields. The `clean` method standardizes the phone number (e.g., removes +, strips leading 0) and stores it in the `phone_number` model field (digits only). Performs uniqueness validation.
- **`MemberLoginForm`**: Includes `email` (optional), `country_code` (optional), and `phone_number_display` (optional). Requires either email or phone to be provided. Formats phone number if provided.

### Views (`accounts/views.py`)
- **`member_login`** (`/masuk/`): Accepts POST data from `MemberLoginForm`. 
  - Validates that either email or phone was provided.
  - If email provided, finds `Member` by email.
  - If phone provided (and no email), finds `Member` by formatted `phone_number`.
  - On success, stores `member.email` in session (`member_email`) and redirects to details.
  - On failure (not found, invalid form), shows error message.
- **`member_logout`** (`/keluar/`): Logs the member out by clearing the session.
- **`MemberSignUpView`** (`/daftar/`): After successful signup, stores `member.email` in session (`member_email`) for auto-login.

### Templates
- `login.html`: Updated to include email and phone number fields (with country code).
- `check_in.html`: Updated to include email and phone number fields (with country code).
- `signup.html`, `member_edit.html`: Include country code and phone number fields.

## Reminders

The reminder system is designed to help gym staff follow up with members at the right time. It automatically generates reminders based on member behavior and provides an admin interface for tracking and resolving them.

### Model (`reminders/models.py`)
- **`Reminder`**: Tracks member reminders with auto-resolution capabilities
  - `member`: ForeignKey (Member)
  - `reminder_type`: CharField (PAYMENT_DUE, NO_VISIT, MEMBERSHIP_EXPIRING)
  - `reason`: TextField (Human-readable explanation)
  - `due_date`: DateField (The specific date this reminder was triggered for)
  - `created_date`: DateTimeField (When reminder was created)
  - `is_resolved`: BooleanField (Whether reminder has been addressed)
  - `resolved_date`: DateTimeField (When reminder was marked resolved)
  - `mark_resolved()`: Method to mark reminder as resolved

**Note**: The `due_date` field stores the actual reminder trigger date (e.g., "3 days before expiry", "on expiry day", "3 days after expiry") rather than the business due date. This ensures multiple reminder phases can be created for the same member/event without conflicts.

### Reminder Types & Logic

#### 1. **Payment Due (Cicilan) - `PAYMENT_DUE`**
- **Trigger**: For payments with `apakah_nyicil=True` (installment payments)
- **Timing**: 3 days before, on the due date, and 3 days after monthly payment due
- **Example**: Payment made Jan 15 → Reminders on Feb 12, Feb 15, Feb 18
- **Auto-Resolution**: When member makes a new installment payment

#### 2. **No Visit - `NO_VISIT`**
- **Trigger**: Member's last visit was exactly 14 days ago
- **Timing**: One-time reminder (prevents spam)
- **Conditions**:
  - Member must be active (`active_until >= today`)
  - Member must have visit history (no reminders for never-visited members)
- **Auto-Resolution**: When member checks in to the gym

#### 3. **Membership Expiring - `MEMBERSHIP_EXPIRING`**
- **Trigger**: Member's `active_until` date approaching
- **Timing**: 3 days before, on expiry date, and 3 days after expiry
- **Auto-Resolution**: When member's `active_until` is extended

### Business Rules

#### **Smart Filtering**
- **New Member Protection**: Payment and expiry reminders only sent to members who joined ≥14 days ago
- **Active Member Focus**: NO_VISIT reminders only for members with active memberships
- **One-Time Logic**: NO_VISIT reminders created once per 14-day gap (prevents daily spam)

#### **Auto-Resolution**
Reminders automatically resolve when conditions change:
- **Payment**: New installment payment made
- **No Visit**: Member visits gym
- **Expiry**: Membership extended beyond the reminder date

### Admin Interface (`reminders/admin.py`)

#### **Current Reminders** (`/admin/reminders/reminder/current/`)
- Shows all unresolved reminders
- Displays: Member (linked), Phone, Type, Due Date, Reason, Actions
- **Actions**: "Selesai" button for each reminder
- Sorted by due date, then creation date

#### **Reminder History** (`/admin/reminders/reminder/history/`)
- Shows all resolved reminders
- Displays: Member (linked), Phone, Type, Due Date, Reason, Created, Resolved
- Provides audit trail of resolved reminders

#### **Quick Access Navigation**
- Added to admin homepage under "Reminders" app
- Direct links to Current Reminders and Reminder History

### Management Command (`reminders/management/commands/generate_reminders.py`)

#### **Daily Automation**
```bash
python manage.py generate_reminders
```

#### **Features**
- **Dry Run Mode**: `--dry-run` flag to preview without creating reminders
- **Auto-Resolution**: Resolves outdated reminders before creating new ones
- **Duplicate Prevention**: Won't create duplicate reminders for same member/type/date
- **Comprehensive Logging**: Shows what was created/resolved

#### **Daily Cron Setup**
```bash
# Add to crontab for daily 6 AM execution:
0 6 * * * /path/to/mulai_web/generate_daily_reminders.sh
```

### Templates (`templates/admin/reminders/reminder/`)
- **`current_reminders.html`**: Current reminders admin view with resolve actions
- **`reminder_history.html`**: Historical reminders for audit trail
- **Member Links**: Click member names to go to member detail page

### Testing (`reminders/tests.py`)
Comprehensive test suite covering:
- **Model Tests**: Reminder creation, resolution, string representation
- **Command Tests**: All reminder types, business rules, auto-resolution
- **Admin Tests**: Views, resolve actions, error handling
- **Edge Cases**: New members, inactive members, duplicate prevention

### Usage Workflow

#### **Daily Operations**
1. **Morning Review**: Check "Current Reminders" in admin
2. **Take Action**: Contact members via phone/WhatsApp 
3. **Selesai**: Click "Selesai" after contacting member
4. **Auto-Resolution**: System automatically resolves when member takes action

#### **Reminder Scenarios**
```
Day 0:  Member makes installment payment
Day 27: "Payment due in 3 days" reminder created
Day 30: "Payment due today" reminder created  
Day 33: "Payment overdue by 3 days" reminder created
```

```
Day 0:  Member visits gym
Day 14: "No visit for 14 days" reminder created
Day 15+: No new reminders (prevents spam)
```

```
Day -3: "Membership expires in 3 days" reminder created
Day 0:  "Membership expires today" reminder created
Day +3: "Membership expired 3 days ago" reminder created
```

## Class Booking

The class booking system allows members to book and manage their attendance for various classes offered at the gym.

### Models (`classes/models.py`)
- **`Class`**: Represents a type of class (e.g., "Yoga").
- **`ClassSchedule`**: Defines the recurring schedule for a class.
- **`ClassInstance`**: A specific instance of a class that members can book.

### Features
- **Members-Only Access**: Class booking is restricted to logged-in members only.
- **Smart Time Filtering**: Only shows upcoming classes; automatically hides classes that have started.
- **Waitlist**: Members can join a waitlist for full classes.
- **Automatic Status Updates**: Class instances are automatically marked as "FULL" or "OPEN".
- **Cancellation**: Members can cancel their bookings with automatic waitlist promotion.
- **Indonesian Localization**: All user-facing content is in Indonesian.

### Automation (`classes/management/commands/generate_class_instances.py`)

The daily management command creates class instances and manages their lifecycle:

```bash
# Generate instances for default 3 days (today, tomorrow, day after)
python manage.py generate_class_instances

# Generate instances for custom number of days
python manage.py generate_class_instances 5

# Generate instances for 1 week
python manage.py generate_class_instances 7
```

#### Command Features
- **Configurable Days**: Accepts a parameter for number of days to generate (default: 3)
- **Past Instance Cleanup**: Automatically marks past instances as "COMPLETED"
- **Duplicate Prevention**: Won't create duplicate instances for the same schedule/date
- **Comprehensive Logging**: Shows creation and completion statistics

#### Daily Cron Setup
```bash
# Standard 3-day generation at 6:00 AM
0 6 * * * /root/mulai_web/generate_daily_class_instances.sh 3

# Extended 7-day generation for special events
0 6 * * * /root/mulai_web/generate_daily_class_instances.sh 7
```

### User Interface
- **Class List**: Shows upcoming classes only (`/kelas/`) - members only
- **Time-Based Filtering**: Automatically hides classes that have already started
- **Real-Time Updates**: Classes disappear from list as their start time passes
- **Class Detail**: Individual class pages with booking functionality (`/kelas/<id>/`)
- **My Account Integration**: Upcoming classes displayed on member account page
- **Mobile-Friendly**: "Lihat Detail" buttons for clear navigation

### Admin Interface
- **Full CRUD Access**: Classes, schedules, and bookings management
- **Class Creation**: Define recurring schedules with day/time patterns
- **Instance Management**: Manually create one-off classes and manage bookings
- **Smart Filtering**: Default view shows only OPEN and FULL instances (active classes)
- **Status Filters**: Access completed/cancelled instances via status filter when needed
- **Member Management**: Add/remove members from class bookings and waitlists

### Booking Rules
- **Login Required**: Only authenticated members can book classes
- **Waitlist System**: Automatic promotion when spots become available
- **No Booking Limits**: Members can book multiple classes
- **Free Cancellation**: No time restrictions on cancellations
- **FIFO Waitlist**: First to join waitlist gets first available spot

### Technical Implementation
- **Time-Based Filtering (`classes/views.py`)**:
  - Uses timezone-aware datetime comparison to filter past classes
  - Combines `date` and `start_time` fields for precise filtering
  - Real-time filtering: `class_datetime > timezone.now()`
  - Supports multiple timezones (UTC server time vs Jakarta local time)

## Payments

### Model (`Payment`)
- `payment_method`: CharField (TRANSFER, QRIS, CASH), default TRANSFER, blank=True.
- `created_by`: ForeignKey (User), SET_NULL, null=True, blank=True. Automatically set in admin.
- `membership_end_date`: Calculated in `save()`, not editable in forms.
- `apakah_nyicil`: BooleanField, default False. Indicates if the payment is part of an installment plan.

### Admin (`visits/admin_init.py`)
- **`CustomPaymentAdmin`**
  - Uses `PaymentAdminForm`.
  - `fieldsets` include `apakah_nyicil` but exclude `created_by`.
  - `save_model` sets `created_by = request.user`.
  - `payment_method` shown as dropdown.
  - `apakah_nyicil` displayed as radio buttons (Ya/Tidak).

### Membership Duration Logic (`Payment.save()`)
1.  **Determine Start Date**:
    - If member active (`active_until >= today`): `start_date = member.active_until + 1 day`.
    - If member inactive (`active_until < today` or `None`): `start_date = payment_date` (or today).
2.  **Calculate Payment `membership_end_date`**:
    - Based on `start_date + duration` (using `relativedelta`).
3.  **Update Member `active_until`**:
    - Always set `member.active_until = self.membership_end_date`.
    - Ensures correct stacking/renewal regardless of current status.

## Tamu (Guest Book)

### Model (`accounts/models.py`)
- **`Tamu`**: For guests who are visiting but not working out.
  - `name`: CharField (Guest's name)
  - `phone_number`: CharField (Contact number)
  - `has_worked_out_before`: CharField (Guest's previous gym experience)
  - `social_media_username`: CharField (Optional social media handle)

### Admin (`accounts/admin.py`)
- **`TamuAdmin`**:
  - Displays guest details in the admin panel.
  - Includes a clickable `whatsapp_link` for easy contact.

### Views (`accounts/views.py`)
- **`tamu_signup_view`** (`/tamu`):
  - Renders a simple form for guests to fill out.
  - On submission, saves the data and shows a success page.

---

## Equipment Guide (Panduan Alat)

### Model (`equipment/models.py`)
- **`Equipment`**: Represents a piece of gym equipment.
  - `name`: CharField (Name of the equipment)
  - `description`: TextField (How to use the equipment)
  - `video_link`: URLField (Link to a YouTube tutorial video)
  - `muscle_group`: CharField (Primary muscle group targeted)
  - `detailed_muscle_group`: CharField (Specific muscle group targeted)

### Performance Optimizations
- **YouTube Thumbnail Loading**: Uses YouTube's thumbnail API instead of loading full iframe videos
- **Progressive Loading**: First 2 videos load immediately, remaining videos load when scrolled into view
- **Lazy Loading**: Intersection Observer API detects when videos come into viewport
- **Caching**: 4-hour page cache + 12-hour data cache to reduce database queries
- **Mobile Optimization**: Reduced bandwidth usage with thumbnail-first approach

### Views (`equipment/views.py`)
- **`equipment_list`** (`/alat/`):
  - Displays a grid of all available equipment, grouped by muscle group
  - **Performance**: Uses cached data and progressive video loading for mobile optimization
  - Each item shows YouTube thumbnail with play button overlay
  - Videos load on demand (click or scroll into view)
- **`equipment_detail`** (`/alat/<slug:slug>/`):
  - Shows the details for a specific piece of equipment, including an embedded YouTube video guide

### Technical Implementation
- **YouTube API Integration**:
  - `get_youtube_video_id()`: Extracts video ID from various YouTube URL formats
  - `get_youtube_thumbnail_url()`: Generates YouTube thumbnail URLs (multiple quality options)
  - `get_youtube_embed_url()`: Creates embed URLs with performance-optimized parameters
- **Lazy Loading Strategy**:
  - Initial page load: Show thumbnails only (fast)
  - Progressive loading: Load first 2 videos automatically, others on scroll
  - Intersection Observer: 25% visibility threshold with 50px margin
  - Click-to-load: Users can click any thumbnail to load video immediately
- **Caching Strategy**:
  - Page-level: 4-hour cache for entire equipment list page
  - Data-level: 12-hour cache for equipment data
  - Cache invalidation: Automatic when equipment is modified via admin

## Products & Sales

### Models (`payments/models.py`)
- **`Package` (Product)**: Represents a membership or service package.
  - `code`: CharField (Unique code for the package, e.g., "M1")
  - `default_price`: DecimalField (The standard price of the package)
  - `description`: CharField (A brief description of the package)
- **`Payment` (Sale)**: Represents a transaction for a package.
  - `member`: ForeignKey (The member who made the purchase)
  - `package`: ForeignKey (The package that was purchased)
  - `amount`: DecimalField (The amount paid)
  - `payment_date`: DateTimeField (When the payment was made)
  - `created_by`: ForeignKey (The admin who recorded the payment)

### Admin (`visits/admin_init.py` & `payments/admin.py`)
- **`PackageAdmin`**:
  - Allows for managing product packages directly from the admin panel.
- **`PaymentAdmin`**:
  - Displays a detailed list of all sales transactions.
  - Automatically assigns the logged-in admin to the `created_by` field on new entries.

### Membership Logic (`Payment.save()`)
- When a `Payment` is saved, it intelligently calculates the member's new `active_until` date.
- If the member is already active, the new membership duration is stacked on top of their existing one.
- If the member is inactive, the new membership starts from the payment date.

---

## Masukkan (Feedback)

### Model (`accounts/models.py`)
- **`Masukkan`**: To collect feedback, critiques, and suggestions.
  - `name`: CharField (Optional)
  - `contact`: CharField (Optional contact info)
  - `feedback`: TextField (The feedback content)

### Admin (`accounts/admin.py`)
- **`MasukkanAdmin`**:
  - Displays all submitted feedback.
  - Provides a link to the details, even for anonymous submissions.

---

## Advanced Membership Analytics

The analytics dashboard provides comprehensive insights into membership trends, revenue projections, and business intelligence to help optimize gym operations and member retention.

### Overview (`visits/admin.py`)

The analytics system is fully integrated into Django admin as a custom admin site extension, accessible via the "Analytics" section on the admin homepage.

### Key Features

#### **📊 Interactive Membership Projections**
- **52-week forward projections** for all membership types
- **Click-to-drill-down**: Click any chart point to see exact member list for that week
- **Real-time calculations** based on current member expiry dates
- **Responsive charts** using Chart.js with smooth animations

#### **🔍 Advanced Member Lookup**
- **Date picker tool**: Find all active members on any specific date
- **Membership type filtering**: Active, Pemula, Semi-Private members
- **AJAX-powered search** with instant results
- **Detailed member information** with payment and visit history

#### **🧠 Smart Alerts & Business Intelligence**
- **Expiry warnings**: Automatic alerts for members expiring in 7/14/30 days
- **Low engagement detection**: Active members who haven't visited recently
- **Growth metrics**: 3-month trends, signup rates, revenue analysis
- **Actionable insights** with direct links to member management

#### **💰 Revenue Projections**
- **12-week revenue forecasts** based on active membership data
- **Package-based calculations** using real pricing data
- **Business trend analysis**: Monthly revenue and growth patterns
- **Visual revenue charts** for quick assessment

#### **📈 Export & Integration**
- **CSV export functionality** for any member list or date range
- **WhatsApp integration**: Direct contact links for all members
- **Bulk operations**: Export filtered member lists for campaigns
- **Admin integration**: Seamless links to existing member management

### Models & Data Sources

The analytics system draws data from multiple models:
- **`Member`**: Membership expiry dates and personal information
- **`Payment`**: Revenue calculations and membership duration
- **`Package`**: Pricing data for revenue projections
- **`Visit`**: Member engagement and activity patterns

### Analytics Views (`visits/admin.py`)

#### **`membership_analytics_view`**
- **URL**: `/admin/analytics/membership/`
- **Purpose**: Main analytics dashboard with charts and insights
- **Features**: 
  - Configurable date ranges (3 months to 2 years)
  - Custom start dates for projection planning
  - Smart alerts and business insights
  - Interactive charts with drill-down functionality

#### **`members_by_date_view`** (AJAX)
- **URL**: `/admin/analytics/members-by-date/`
- **Purpose**: Get member list for specific date and membership type
- **Parameters**: `date` (YYYY-MM-DD), `type` (active/pemula/semi_private)
- **Returns**: JSON with member details and WhatsApp links

#### **`member_details_view`** (AJAX)
- **URL**: `/admin/analytics/member-details/<id>/`
- **Purpose**: Detailed member information with history
- **Returns**: Payment history, visit patterns, contact information

#### **`export_members_view`**
- **URL**: `/admin/analytics/export-members/`
- **Purpose**: CSV export for member lists
- **Parameters**: `date`, `type` for filtering
- **Returns**: CSV file with member data

### Business Intelligence Calculations

#### **Smart Alerts Logic**
```python
# Members expiring soon
expiring_7_days = Member.objects.filter(
    active_until__gte=now,
    active_until__lte=now + timedelta(days=7)
).count()

# Low engagement detection
low_visit_members = Member.objects.filter(
    active_until__gte=now
).exclude(
    visit__check_in_time__gte=now - timedelta(days=14)
).count()
```

#### **Revenue Projections**
```python
# Weekly revenue estimate
estimated_revenue = active_members * (avg_package_price / 4)
```

#### **Membership Projections**
```python
# Members active by end of week
week_end_datetime = timezone.make_aware(
    timezone.datetime.combine(week_end, timezone.datetime.min.time())
)
active_count = Member.objects.filter(
    active_until__gte=week_end_datetime
).count()
```

### User Interface & UX

#### **Control Panel**
- **Date range selector**: 3 months, 6 months, 1 year, 2 years
- **Custom start date**: Plan projections from any date
- **Member lookup tool**: Quick date-based member search
- **Update controls**: Refresh charts without page reload

#### **Smart Alerts Panel**
- **Color-coded alerts**: Warning (orange), Info (blue)
- **Actionable messages**: Direct links to member management
- **Real-time calculations**: Based on current membership data

#### **Interactive Features**
- **Chart click events**: Click any data point to see member details
- **Modal popups**: Member lists and detailed information overlays
- **Responsive design**: Works perfectly on desktop and mobile
- **WhatsApp integration**: One-click contact for any member

### Daily Operations Workflow

#### **Morning Review**
1. Check smart alerts for expiring memberships
2. Review low-engagement member alerts
3. Plan follow-up actions via WhatsApp links

#### **Business Planning**
1. Analyze revenue projections for budget planning
2. Use member lookup for campaign targeting
3. Export member lists for marketing initiatives

#### **Member Management**
1. Click chart points to see weekly member lists
2. Use detailed member view for personalized follow-up
3. Track payment history and visit patterns

### Admin Integration

The analytics dashboard is seamlessly integrated into the existing custom admin site:

```python
# Added to CustomAdminSite.get_app_list()
analytics_app = {
    "name": "Analytics",
    "app_label": "analytics", 
    "models": [{
        "name": "Membership Projections",
        "admin_url": reverse("admin:membership-analytics"),
    }],
}
```

### Performance & Scalability

- **Efficient queries**: Optimized database queries with proper indexing
- **AJAX loading**: Smooth user experience with asynchronous data loading
- **Cached calculations**: Smart caching for frequently accessed data
- **Mobile responsive**: Works efficiently on all device sizes

### Security & Permissions

- **Staff-only access**: All analytics views require `is_staff` permission
- **Permission checking**: Consistent security across all endpoints
- **Data protection**: No sensitive data exposure to unauthorized users

---

## Admin Interface Enhancements

The admin interface has been enhanced with consistent member search functionality across all forms to improve operational efficiency and user experience.

### Member Search & Autocomplete

#### **Universal Member Search**
All admin forms that reference members now include autocomplete search functionality:
- **Payments** (`/admin/payments/payment/add/`) → ✅ Member autocomplete search
- **Reminders** (`/admin/reminders/reminder/add/`) → ✅ Member autocomplete search  
- **Visits** (`/admin/visits/visit/add/`) → ✅ Member autocomplete search
- **Sales** (`/admin/purchases/sale/add/`) → ✅ Member autocomplete search

#### **Search Capabilities**
- **Multi-field search**: Searches across member name, email, and phone number simultaneously
- **Real-time filtering**: Instant results as you type
- **Consistent UX**: Same search experience across all admin forms
- **Mobile responsive**: Works efficiently on all device sizes

#### **Technical Implementation**
```python
# Added to all admin classes that reference Member model
autocomplete_fields = ["member"]
search_fields = ("member__name", "member__email", "member__phone_number")
```

#### **Admin Site Architecture**
- **Custom Admin Site**: All models registered to `CustomAdminSite` for consistency
- **Unified Registration**: Ensures autocomplete functionality works across all admin forms
- **Member Model Admin**: Configured with proper `search_fields` to enable autocomplete

## Troubleshooting

### SSL Certificate Issues
- **Error 526**: Usually means expired certificate or DNS configuration mismatch
- **Check certificate status**: `sudo certbot certificates`
- **Manual renewal**: `sudo certbot renew --force-renewal`
- **Test auto-renewal**: `sudo certbot renew --dry-run`

### Common Commands
- **Restart services**: `sudo systemctl reload nginx && docker restart mulai_web`
- **Check logs**: `docker logs mulai_web`
- **Nginx test**: `sudo nginx -t`

---

## Testing

This project uses Django's built-in `TestCase` for unit testing. The tests are located in the `tests.py` file within each application directory (`accounts`, `visits`, `payments`, `equipment`, `purchases`, and `reminders`).

### Reminder Tests
The `reminders` app includes comprehensive tests for:
- **Model Tests**: Reminder creation, resolution, string representation, and all reminder type choices
- **Management Command Tests**: Auto-resolution logic, business rules (14-day member protection), and reminder generation for all three types
- **Admin Tests**: Current reminders view, reminder history view, resolve actions, and error handling
- **Edge Case Coverage**: New members, inactive members, duplicate prevention, and member visit patterns
- **Multi-Phase Validation**: Comprehensive test ensuring all three phases of membership expiry reminders are generated correctly ("3 hari lagi", "hari ini", "3 hari lalu")

### Payment Tests
The `payments` app includes comprehensive tests for:
- Payment model functionality (membership duration calculations, field defaults)
- Admin form validation (including `apakah_nyicil` field configuration)
- Custom duration validation logic

### Analytics Tests
The `visits` app includes comprehensive analytics tests for:
- **View Access Control**: Permission testing for admin and regular users
- **Data Calculations**: Membership projection accuracy and business insights
- **AJAX Endpoints**: Member lookup, details view, and data export functionality
- **Smart Alerts**: Expiry warnings and engagement detection logic
- **Revenue Projections**: Financial forecasting and package-based calculations
- **Export Features**: CSV generation and data integrity validation
- **Error Handling**: Invalid date formats and permission-denied scenarios

### Running Tests

To run all tests for the entire project, use the following command:

```bash
python manage.py test
```

To run tests for a specific application, append the application name:

```bash
python manage.py test accounts
python manage.py test visits
python manage.py test reminders
```

### Continuous Integration

A GitHub Actions workflow is configured in `.github/workflows/deploy.yml` to automatically run all tests on every push to the `main` branch. The deployment to the production server will only proceed if all tests pass, ensuring a more stable and reliable deployment process.
