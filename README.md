# Mulai Gym Web App

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
- **`check_in_page`**
  1. Checks session for `member_email`.
  2. If logged in:
     - Tries auto check-in (validates active member, no active visit).
     - Renders success/failure template.
  3. If not logged in or auto-check-in fails:
     - Shows email OR phone number form (`check_in.html`).
     - On POST:
       - If email provided, finds `Member` by email.
       - If phone provided, formats phone (handles country code, strips leading zeros) and finds `Member` by `phone_number`.
       - If neither provided, shows error.
       - If `Member` found:
         - **Logs user in:** Stores `member.email` in session (`member_email`) immediately.
         - Validates active member status -> renders failure if inactive.
         - Validates no active visit -> renders failure if already checked in.
         - Creates `Visit`, renders success (`quick_check_in.html`).
       - If `Member` not found, shows error.
- **`check_out_page`**
  1. Checks session for `member_email` (renders fail if not logged in).
  2. Tries auto check-out:
     - Finds latest active `Visit` for member.
     - Sets `check_out_time`, saves `Visit`.
     - Renders success/failure template.
- **`forget_member`**
  - Clears `member_email` from session.

### Check-in/Out Flow Diagram
```mermaid
graph TD
    A[Visit Check-in Page] --> B{Logged In?}
    B -->|Yes| C{Has Active Visit?}
    B -->|No| D[Show Email/Phone Form]
    C -->|Yes| E[Show Failure: Already Checked In]
    C -->|No| F{Member Active?}
    F -->|Yes| G[Auto Check-in]
    F -->|No| H[Show Failure: Inactive Member]
    D --> I[Submit Email or Phone]
    I --> I1{Email or Phone Provided?}
    I1 -->|No| I2[Show Error Message]
    I1 -->|Yes| J{Find Member}
    J -->|Found| J1[Store Email in Session<br>User Now Logged In]
    J -->|Not Found| J2[Show Error: Member Not Found]
    J1 --> J3{Member Active?}
    J3 -->|No| H
    J3 -->|Yes| J4{Has Active Visit?}
    J4 -->|Yes| E
    J4 -->|No| K[Create Visit]
    K --> M[Show Success Message]

    N[Visit Check-out Page] --> O{Logged In?}
    O -->|Yes| P{Has Active Visit?}
    O -->|No| Q[Show Failure: Not Logged In]
    P -->|Yes| R[Auto Check-out]
    P -->|No| S[Show Failure: No Active Visit]
```

### Validations & Messages
- Check-in:
  - Must provide Email or Phone Number.
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
- **`member_login`**: Accepts POST data from `MemberLoginForm`. 
  - Validates that either email or phone was provided.
  - If email provided, finds `Member` by email.
  - If phone provided (and no email), finds `Member` by formatted `phone_number`.
  - On success, stores `member.email` in session (`member_email`) and redirects to details.
  - On failure (not found, invalid form), shows error message.
- **`MemberSignUpView`**: After successful signup, stores `member.email` in session (`member_email`) for auto-login.

### Templates
- `login.html`: Updated to include email and phone number fields (with country code).
- `check_in.html`: Updated to include email and phone number fields (with country code).
- `signup.html`, `member_edit.html`: Include country code and phone number fields.

## Payments

### Model (`Payment`)
- `payment_method`: CharField (TRANSFER, QRIS, CASH), default TRANSFER, blank=True.
- `created_by`: ForeignKey (User), SET_NULL, null=True, blank=True. Automatically set in admin.
- `membership_end_date`: Calculated in `save()`, not editable in forms.

### Admin (`visits/admin_init.py`)
- **`CustomPaymentAdmin`**
  - Uses `PaymentAdminForm`.
  - `fieldsets` exclude `created_by`.
  - `save_model` sets `created_by = request.user`.
  - `payment_method` shown as dropdown.

### Membership Duration Logic (`Payment.save()`)
1.  **Determine Start Date**:
    - If member active (`active_until >= today`): `start_date = member.active_until + 1 day`.
    - If member inactive (`active_until < today` or `None`): `start_date = payment_date` (or today).
2.  **Calculate Payment `membership_end_date`**:
    - Based on `start_date + duration` (using `relativedelta`).
3.  **Update Member `active_until`**:
    - Always set `member.active_until = self.membership_end_date`.
    - Ensures correct stacking/renewal regardless of current status.
