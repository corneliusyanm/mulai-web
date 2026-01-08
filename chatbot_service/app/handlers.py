"""
Message handlers for the WhatsApp chatbot.
Handles incoming messages and generates appropriate responses.
"""

from app.state import get_state, set_state, clear_state
from app.gym_api import (
    get_available_classes,
    get_member_by_phone,
    book_class,
    join_waitlist,
    cancel_booking,
    get_my_bookings,
)


# Keywords that trigger different flows
BOOKING_KEYWORDS = ["book", "class", "kelas", "booking", "classes"]
MY_BOOKINGS_KEYWORDS = [
    "my booking", "my bookings", "my class", "my classes", "mybooking", "mybookings"
]
CANCEL_KEYWORDS = ["cancel", "batal", "exit", "quit", "stop"]
YES_KEYWORDS = ["yes", "ya", "y", "ok", "oke", "yup", "sure"]
NO_KEYWORDS = ["no", "tidak", "nope", "n", "ga", "gak"]
HELP_KEYWORDS = ["help", "bantuan", "menu", "hi", "hello", "halo"]


async def handle_message(phone: str, message: str) -> str:
    """
    Main message handler. Routes to appropriate handler based on state and message.

    Args:
        phone: Sender's phone number (e.g., 6289654108308)
        message: Message content

    Returns:
        Response message to send back
    """
    msg = message.strip().lower()
    state = get_state(phone)
    mode = state.get("mode", "idle")

    # Cancel always works
    if any(kw in msg for kw in CANCEL_KEYWORDS):
        clear_state(phone)
        return "No worries! Let me know if you need anything else. 👋"

    # Help/menu
    if mode == "idle" and any(kw == msg for kw in HELP_KEYWORDS):
        return get_help_message()

    # Route based on current mode
    if mode == "idle":
        # Check my bookings first (more specific)
        if any(kw in msg for kw in MY_BOOKINGS_KEYWORDS):
            return await handle_my_bookings(phone)
        if any(kw in msg for kw in BOOKING_KEYWORDS):
            return await handle_start_booking(phone)
        return get_help_message()

    elif mode == "selecting_class":
        return await handle_class_selection(phone, msg)

    elif mode == "confirm_waitlist":
        return await handle_waitlist_confirmation(phone, msg)

    elif mode == "viewing_bookings":
        return await handle_cancel_selection(phone, msg)

    elif mode == "confirm_cancel":
        return await handle_cancel_confirmation(phone, msg)

    # Fallback
    return get_help_message()


def get_help_message() -> str:
    """Return the help/welcome message."""
    return (
        "Hey there! 👋\n\n"
        "I can help you book a class at Mulai Gym.\n\n"
        "*book* - See available classes and book one\n"
        "*my bookings* - View your booked classes\n\n"
        "Type *cancel* anytime to exit."
    )


async def handle_start_booking(phone: str) -> str:
    """
    Start the class booking flow.
    Shows available classes and waits for selection.
    """
    # Look up member first
    member = await get_member_by_phone(phone)

    if not member:
        return (
            "Hmm, I couldn't find your account with this phone number.\n\n"
            "Make sure you're messaging from the number registered with Mulai Gym. "
            "If you need help, just reach out to our admin! 😊"
        )

    if not member.get("is_active"):
        return (
            f"Hey {member['name']}! 👋\n\n"
            "Looks like your membership isn't active right now.\n\n"
            "Please contact our admin to renew, and then you can book classes again!"
        )

    # Get available classes
    classes = await get_available_classes()

    if not classes:
        return (
            "No classes available at the moment.\n\n"
            "Check back later or contact our admin for the schedule! 📅"
        )

    # Filter classes member can book
    bookable_classes = []
    for c in classes:
        requires = c.get("requires", "")
        if requires == "silver" and not member.get("can_book_pemula"):
            continue
        if requires == "gold" and not member.get("can_book_semi_private"):
            continue
        bookable_classes.append(c)

    if not bookable_classes:
        return (
            f"Hey {member['name']}! 👋\n\n"
            "There are classes available, but your current membership doesn't include them.\n\n"
            "Contact our admin to upgrade your membership if you'd like to join! 💪"
        )

    # Build class list message
    lines = [f"Hey {member['name']}! Here are the upcoming classes:\n"]

    for i, c in enumerate(bookable_classes, 1):
        status = ""
        if c["status"] == "FULL":
            status = " *(FULL - waitlist available)*"
        elif c["available_slots"] <= 2:
            status = f" *({c['available_slots']} spots left)*"

        lines.append(f"{i}. {c['class_name']} - {c['date']}, {c['start_time']}{status}")

    lines.append("\nReply with a number to book, or *cancel* to exit.")

    # Save state
    set_state(phone, mode="selecting_class", classes=bookable_classes, member=member)

    return "\n".join(lines)


async def handle_my_bookings(phone: str) -> str:
    """
    Show member's current bookings and waitlist entries.
    Allows cancellation by replying with a number.
    """
    member = await get_member_by_phone(phone)

    if not member:
        return (
            "Hmm, I couldn't find your account with this phone number.\n\n"
            "Make sure you're messaging from the number registered with Mulai Gym."
        )

    bookings = await get_my_bookings(member["id"])

    if not bookings:
        return (
            f"Hey {member['name']}! 📋\n\n"
            "You don't have any bookings yet.\n\n"
            "Type *book* to see available classes!"
        )

    # Build numbered list (booked first, then waitlisted)
    all_bookings = []
    booked = [b for b in bookings if b.get("booking_status") == "booked"]
    waitlisted = [b for b in bookings if b.get("booking_status") == "waitlisted"]

    lines = [f"Hey {member['name']}! Here are your bookings: 📋\n"]

    idx = 1
    if booked:
        lines.append("*✅ Booked:*")
        for b in booked:
            lines.append(f"{idx}. {b['class_name']} - {b['date']}, {b['start_time']}")
            all_bookings.append(b)
            idx += 1
        lines.append("")

    if waitlisted:
        lines.append("*⏳ Waitlisted:*")
        for w in waitlisted:
            lines.append(f"{idx}. {w['class_name']} - {w['date']}, {w['start_time']}")
            all_bookings.append(w)
            idx += 1
        lines.append("")

    lines.append("Reply with a number to cancel, or *book* to book more.")

    # Save state for cancellation
    set_state(phone, mode="viewing_bookings", bookings=all_bookings, member=member)

    return "\n".join(lines)


async def handle_class_selection(phone: str, msg: str) -> str:
    """
    Handle class number selection.
    Books the class or asks about waitlist if full.
    """
    state = get_state(phone)
    classes = state.get("classes", [])
    member = state.get("member")

    if not classes or not member:
        clear_state(phone)
        return "Something went wrong. Please type *book* to start over."

    # Parse selection
    try:
        selection = int(msg)
        if selection < 1 or selection > len(classes):
            raise ValueError()
    except ValueError:
        return (
            f"Please reply with a number between 1 and {len(classes)}, "
            "or type *cancel* to exit."
        )

    selected_class = classes[selection - 1]

    # If class is full, ask about waitlist
    if selected_class["status"] == "FULL":
        set_state(phone, mode="confirm_waitlist", selected_class=selected_class)
        return (
            f"*{selected_class['class_name']}* on {selected_class['date']} at {selected_class['start_time']} is full.\n\n"
            "Would you like to join the waitlist? We'll let you know if a spot opens up.\n\n"
            "Reply *yes* or *no*."
        )

    # Book the class
    result = await book_class(member["id"], selected_class["id"])

    if result.get("success"):
        clear_state(phone)
        return (
            f"You're all set! ✅\n\n"
            f"*{selected_class['class_name']}*\n"
            f"📅 {selected_class['date']} at {selected_class['start_time']}\n\n"
            f"See you there, {member['name']}! 💪"
        )
    else:
        error_msg = result.get("message", "Unknown error")
        clear_state(phone)
        return f"Oops, couldn't complete the booking: {error_msg}\n\nPlease try again or contact our admin."


async def handle_waitlist_confirmation(phone: str, msg: str) -> str:
    """
    Handle yes/no response for waitlist confirmation.
    """
    state = get_state(phone)
    selected_class = state.get("selected_class")
    member = state.get("member")

    if not selected_class or not member:
        clear_state(phone)
        return "Something went wrong. Please type *book* to start over."

    if any(kw == msg for kw in YES_KEYWORDS):
        # Join waitlist
        result = await join_waitlist(member["id"], selected_class["id"])

        if result.get("success"):
            clear_state(phone)
            return (
                f"Got it! You're on the waitlist for:\n\n"
                f"*{selected_class['class_name']}*\n"
                f"📅 {selected_class['date']} at {selected_class['start_time']}\n\n"
                f"We'll let you know if a spot opens up, {member['name']}! 🤞"
            )
        else:
            error_msg = result.get("message", "Unknown error")
            clear_state(phone)
            return f"Couldn't add you to the waitlist: {error_msg}\n\nPlease try again or contact our admin."

    elif any(kw == msg for kw in NO_KEYWORDS):
        clear_state(phone)
        return "No problem! Let me know if you'd like to book a different class. Just type *book* anytime. 👍"

    else:
        return "Please reply *yes* to join the waitlist, or *no* to go back."


async def handle_cancel_selection(phone: str, msg: str) -> str:
    """
    Handle booking number selection for cancellation.
    """
    state = get_state(phone)
    bookings = state.get("bookings", [])
    member = state.get("member")

    if not bookings or not member:
        clear_state(phone)
        return "Something went wrong. Please type *my bookings* to start over."

    # Check if user wants to book instead
    if any(kw in msg for kw in BOOKING_KEYWORDS):
        clear_state(phone)
        return await handle_start_booking(phone)

    # Parse selection
    try:
        selection = int(msg)
        if selection < 1 or selection > len(bookings):
            raise ValueError()
    except ValueError:
        return (
            f"Please reply with a number between 1 and {len(bookings)}, "
            "*book* to book more, or *cancel* to exit."
        )

    selected_booking = bookings[selection - 1]
    booking_type = "waitlist" if selected_booking.get("booking_status") == "waitlisted" else "booking"

    # Ask for confirmation
    set_state(phone, mode="confirm_cancel", selected_booking=selected_booking, member=member)

    return (
        f"Are you sure you want to cancel this {booking_type}?\n\n"
        f"*{selected_booking['class_name']}*\n"
        f"📅 {selected_booking['date']} at {selected_booking['start_time']}\n\n"
        "Reply *yes* to confirm or *no* to go back."
    )


async def handle_cancel_confirmation(phone: str, msg: str) -> str:
    """
    Handle yes/no response for cancel confirmation.
    """
    state = get_state(phone)
    selected_booking = state.get("selected_booking")
    member = state.get("member")

    if not selected_booking or not member:
        clear_state(phone)
        return "Something went wrong. Please type *my bookings* to start over."

    if any(kw == msg for kw in YES_KEYWORDS):
        # Cancel the booking
        result = await cancel_booking(member["id"], selected_booking["id"])

        if result.get("success"):
            clear_state(phone)
            booking_type = "waitlist spot" if selected_booking.get("booking_status") == "waitlisted" else "booking"
            return (
                f"Done! Your {booking_type} has been cancelled. ✅\n\n"
                f"*{selected_booking['class_name']}*\n"
                f"📅 {selected_booking['date']} at {selected_booking['start_time']}\n\n"
                "Type *book* to book another class or *my bookings* to see your bookings."
            )
        else:
            error_msg = result.get("message", "Unknown error")
            clear_state(phone)
            return f"Couldn't cancel: {error_msg}\n\nPlease try again or contact our admin."

    elif any(kw == msg for kw in NO_KEYWORDS):
        clear_state(phone)
        return "No problem! Your booking is still active. 👍\n\nType *my bookings* to see your bookings."

    else:
        return "Please reply *yes* to confirm cancellation, or *no* to keep your booking."
