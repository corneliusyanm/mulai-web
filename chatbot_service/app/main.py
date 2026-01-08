"""
FastAPI application for Mulai Gym WhatsApp Chatbot.
Receives webhooks from 360dialog and responds via their API.
"""

import logging

from fastapi import FastAPI, HTTPException, Request

from app.config import get_settings
from app.dialog360 import send_text_message
from app.handlers import handle_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mulai Gym WhatsApp Chatbot",
    description="Book gym classes via WhatsApp",
    version="1.0.0",
)


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "mulai-gym-chatbot"}


@app.post("/webhook")
async def webhook(request: Request):
    """
    Webhook endpoint for 360dialog.
    Receives incoming WhatsApp messages and responds.

    360dialog payload structure:
    {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{"from": "628xxx", "text": {"body": "..."}}]
                }
            }]
        }]
    }
    """
    try:
        payload = await request.json()
        logger.info("Webhook received: %s", payload)

        # Extract messages from nested 360dialog structure
        messages = _extract_messages(payload)
        logger.info("Processing %d message(s)", len(messages))

        for msg in messages:
            if msg.get("type") != "text":
                logger.debug("Skipping non-text message: %s", msg.get("type"))
                continue

            phone = msg.get("from", "")
            text = msg.get("text", {}).get("body", "")

            if not phone or not text:
                logger.warning("Missing phone or text in message")
                continue

            logger.info("Message from %s: %s", phone, text[:50])

            response_text = await handle_message(phone, text)
            logger.info("Response: %s...", response_text[:50])

            await send_text_message(phone, response_text)

        return {"status": "ok"}

    except Exception as e:
        logger.exception("Webhook error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _extract_messages(payload: dict) -> list[dict]:
    """Extract messages from 360dialog webhook payload."""
    messages = []

    # Standard 360dialog structure
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages.extend(value.get("messages", []))

    # Fallback: top-level messages (for direct testing)
    if not messages:
        messages = payload.get("messages", [])

    return messages


@app.get("/test-send")
async def test_send():
    """
    Send a test message to your registered phone number.
    Only works with sandbox (must use the number that got the API key).
    """
    settings = get_settings()

    if not settings.my_phone_number:
        return {"error": "MY_PHONE_NUMBER not configured in .env"}

    result = await send_text_message(
        settings.my_phone_number,
        "Hello from Mulai Gym Chatbot! Type *book* to see available classes.",
    )
    return {"status": "sent", "result": result}


@app.post("/simulate")
async def simulate(phone: str, message: str):
    """
    Simulate a conversation without sending real WhatsApp messages.
    Useful for testing the bot locally.

    Args:
        phone: Simulated sender phone number
        message: Message content

    Returns:
        Bot's response
    """
    response = await handle_message(phone, message)
    return {"from": phone, "message": message, "response": response}
