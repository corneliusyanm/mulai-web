# Mulai Gym Web App

## Check-in/Check-out Flow

### Session
- 1-year duration
- Key: `member_email`
- Persists across check-in/out

### Check-in
1. If logged in:
   - Auto check-in if active member & no active visit
   - Show failure if inactive or has active visit
2. If not logged in:
   - Show email form
   - On submit: validate & create visit if valid

### Check-out
1. If logged in:
   - Auto check-out if has active visit
   - Show failure if no active visit
2. If not logged in:
   - Show failure

### Flow Diagram
```mermaid
graph TD
    A[Visit Check-in Page] --> B{Logged In?}
    B -->|Yes| C{Has Active Visit?}
    B -->|No| D[Show Email Form]
    C -->|Yes| E[Show Failure: Already Checked In]
    C -->|No| F{Member Active?}
    F -->|Yes| G[Auto Check-in]
    F -->|No| H[Show Failure: Inactive Member]
    D --> I[Submit Email]
    I --> J{Member Exists & Active?}
    J -->|Yes| K[Create Visit]
    J -->|No| L[Show Failure Message]
    K --> M[Store Email in Session]

    N[Visit Check-out Page] --> O{Logged In?}
    O -->|Yes| P{Has Active Visit?}
    O -->|No| Q[Show Failure: Not Logged In]
    P -->|Yes| R[Auto Check-out]
    P -->|No| S[Show Failure: No Active Visit]
```

### Validations & Messages
- Check-in:
  - Must be active member
  - No duplicate active visits
  - Messages: "Already Checked In", "Membership Expired"
- Check-out:
  - Must be logged in
  - Must have active visit
  - Messages: "Not Logged In", "No Active Visit Found"
