# Mulai Gym WhatsApp Chatbot

A WhatsApp chatbot that lets gym members book classes via chat. Built with FastAPI and 360dialog API.

## DEMO Video Link
https://www.youtube.com/watch?v=P_D_aLeRnpc

## Background

**Real problem this solves:** At Mulai Gym, members often forget to book their classes through the website. This is especially common with older members who aren't tech-savvy. The result? Trainers get surprised by unregistered attendees, and gym admins end up manually booking for members after back-and-forth messages like:

> Admin: "Hi miss, today do you want to take class as usual, 18.15?"  
> Member: "Yes"  
> *(Admin manually books the class)*

Or members message in the morning: "Please help book class today 18.15." and admins have to do it for them.

**This chatbot automates that.** Members simply message via WhatsApp to see available classes and book with a few taps — no website, no manual admin intervention needed.

## Features

- **Book Classes** — View upcoming classes and book with a number reply
- **Join Waitlist** — If class is full, join the waitlist automatically
- **View Bookings** — See all your booked and waitlisted classes
- **Cancel Bookings** — Cancel any booking or leave waitlist
- **Membership Validation** — Only shows classes your membership includes

## Conversation Flow

### Booking a Class

```
User: book
Bot:  Hey Cornelius! Here are the upcoming classes:

      1. Semi Private - 2026-01-08, 07:00 (2 spots left)
      2. Kelas Pemula (Push) - 2026-01-08, 08:00
      3. Semi Private - 2026-01-08, 16:15 (FULL - waitlist available)
      
      Reply with a number to book, or cancel to exit.

User: 1
Bot:  You're all set! ✅
      
      Semi Private
      📅 2026-01-08 at 07:00
      
      See you there, Cornelius! 💪
```

### Joining Waitlist

```
User: 3
Bot:  Semi Private on 2026-01-08 at 16:15 is full.
      
      Would you like to join the waitlist?
      Reply yes or no.

User: yes
Bot:  Got it! You're on the waitlist for:
      
      Semi Private
      📅 2026-01-08 at 16:15
      
      We'll let you know if a spot opens up! 🤞
```

### View & Cancel Bookings

```
User: my bookings
Bot:  Hey Cornelius! Here are your bookings: 📋

      ✅ Booked:
      1. Semi Private - 2026-01-08, 07:00
      
      ⏳ Waitlisted:
      2. Semi Private - 2026-01-08, 16:15
      
      Reply with a number to cancel, or book to book more.

User: 2
Bot:  Are you sure you want to cancel this waitlist?
      
      Semi Private
      📅 2026-01-08 at 16:15
      
      Reply yes to confirm or no to go back.

User: yes
Bot:  Done! Your waitlist spot has been cancelled. ✅
```

## Quick Start

### 1. Setup

```bash
cd chatbot_service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
```

### 2. Configure `.env`

```env
# 360dialog API (get key by sending "START" to WhatsApp +55 11 4673 3492)
D360_API_KEY=your_api_key_here
MY_PHONE_NUMBER=6289654108308

# Data source (true = mock data, false = real Mulai Gym API)
USE_MOCK_DATA=true
GYM_API_BASE_URL=http://localhost:8000
GYM_API_KEY=your_gym_api_key
```

### 3. Run

```bash
uvicorn app.main:app --reload --port 8001
```

### 4. Test Locally

```bash
# Show help
curl -X POST "http://localhost:8001/simulate?phone=6281234567890&message=hello"

# Book flow
curl -X POST "http://localhost:8001/simulate?phone=6281234567890&message=book"
curl -X POST "http://localhost:8001/simulate?phone=6281234567890&message=1"

# View bookings
curl -X POST "http://localhost:8001/simulate?phone=6281234567890&message=my%20bookings"
```

### 5. Test with Real WhatsApp

```bash
# Start ngrok
ngrok http 8001

# Set webhook URL in 360dialog
curl -X POST https://waba-sandbox.360dialog.io/v1/configs/webhook \
  -H "D360-API-KEY: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_NGROK_URL/webhook"}'

# Send message to the sandbox WhatsApp number
```

## Running Tests

```bash
cd chatbot_service
source venv/bin/activate
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_handlers.py
```

## Project Structure

```
chatbot_service/
├── app/
│   ├── main.py         # FastAPI app, webhook endpoint
│   ├── config.py       # Environment settings
│   ├── dialog360.py    # 360dialog API client
│   ├── gym_api.py      # Mulai Gym API client
│   ├── handlers.py     # Conversation logic
│   ├── state.py        # In-memory state management
│   └── mock_data.py    # Mock data for testing
├── tests/
│   ├── test_api.py     # API endpoint tests
│   ├── test_handlers.py # Handler logic tests
│   └── test_mock_data.py # Mock data tests
├── requirements.txt
├── pyproject.toml      # Pytest config
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/webhook` | POST | 360dialog webhook receiver |
| `/simulate` | POST | Test conversation locally |
| `/test-send` | GET | Send test message to yourself |

## Switching to Real Data

To connect to a real Mulai Gym server:

1. Set in `.env`:
   ```
   USE_MOCK_DATA=false
   GYM_API_BASE_URL=https://mulaigym.id
   GYM_API_KEY=your_secret_key
   ```

## Keywords Reference

| Action | Keywords |
|--------|----------|
| Start booking | book, class, kelas, booking, classes |
| View bookings | my bookings, my classes |
| Confirm | yes, ya, y, ok, oke, yup, sure |
| Decline | no, tidak, nope, n, ga, gak |
| Cancel/Exit | cancel, batal, exit, quit, stop |
| Help | help, hi, hello, halo, menu |

## Notes

**Why this use case:** This solves a real problem at a real gym. The chatbot is already integrated with an existing Django backend and can be deployed to production immediately.

**Design decisions:**
- **Keyword matching over NLP** — Simple, predictable, and works for the target audience (gym members who just want to book quickly). No ML overhead or misinterpretation risks.
- **State machine for conversation** — Each user has a mode (idle → selecting_class → confirm_waitlist). Clear flow, easy to debug.
- **Mock data layer** — `gym_api.py` switches between mock and real API via config. Allows full testing without external dependencies.
- **In-memory state** — Good enough for a chatbot where conversations are short-lived. For production scale, would swap to Redis.
