"""
360dialog WhatsApp API client for sending messages.
Docs: https://docs.360dialog.com/docs/waba-messaging/sandbox
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class Dialog360Error(Exception):
    """Raised when 360dialog API call fails."""


async def send_text_message(to: str, text: str) -> dict:
    """
    Send a text message via 360dialog API.

    Args:
        to: Phone number in format 628xxx (no + prefix)
        text: Message content

    Returns:
        API response dict

    Raises:
        Dialog360Error: If the API call fails
    """
    settings = get_settings()

    url = f"{settings.d360_base_url}/v1/messages"
    headers = {
        "D360-API-KEY": settings.d360_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    logger.info("Sending message to %s via 360dialog", to)

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            result = response.json()

            if response.status_code >= 400:
                logger.error(
                    "360dialog API error: status=%d, body=%s",
                    response.status_code,
                    result,
                )
                raise Dialog360Error(f"API error: {result}")

            logger.info("Message sent successfully: %s", result.get("messages", []))
            return result

    except httpx.TimeoutException as e:
        logger.error("360dialog timeout: %s", e)
        raise Dialog360Error("Request timed out") from e
    except httpx.RequestError as e:
        logger.error("360dialog request error: %s", e)
        raise Dialog360Error(f"Request failed: {e}") from e
