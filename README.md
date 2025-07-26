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

### Forms (`accounts/forms.py`)
- **`MemberSignUpForm`, `MemberEditForm`**: Include `country_code` (default +62) and `phone_number_display` fields. The `clean` method standardizes the phone number (e.g., removes +, strips leading 0) and stores it in the `phone_number` model field (digits only). Performs uniqueness validation.
- **`MemberLoginForm`**: Includes `email` (optional), `country_code` (optional), and `phone_number_display` (optional). Requires either email or phone to be provided. Formats phone number if provided.

### Views (`accounts/views.py`)
- **`member_login`** (`/accounts/masuk/`): Accepts POST data from `MemberLoginForm`. 
  - Validates that either email or phone was provided.
  - If email provided, finds `Member` by email.
  - If phone provided (and no email), finds `Member` by formatted `phone_number`.
  - On success, stores `member.email` in session (`member_email`) and redirects to details.
  - On failure (not found, invalid form), shows error message.
- **`member_logout`** (`/accounts/keluar/`): Logs the member out by clearing the session.
- **`MemberSignUpView`** (`/accounts/daftar/`): After successful signup, stores `member.email` in session (`member_email`) for auto-login.

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
  - `due_date`: DateField (The date this reminder is for)
  - `created_date`: DateTimeField (When reminder was created)
  - `is_resolved`: BooleanField (Whether reminder has been addressed)
  - `resolved_date`: DateTimeField (When reminder was marked resolved)
  - `mark_resolved()`: Method to mark reminder as resolved

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
- **Expiry**: Membership extended significantly

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

### Views (`equipment/views.py`)
- **`equipment_list`** (`/alat/`):
  - Displays a grid of all available equipment, grouped by muscle group.
  - Each item links to the detail page.
- **`equipment_detail`** (`/alat/<slug:slug>/`):
  - Shows the details for a specific piece of equipment, including an embedded YouTube video guide.

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

### Payment Tests
The `payments` app includes comprehensive tests for:
- Payment model functionality (membership duration calculations, field defaults)
- Admin form validation (including `apakah_nyicil` field configuration)
- Custom duration validation logic

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
