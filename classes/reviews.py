"""Penilaian Kelas: the queue of "how was it?", and the words it is asked in.

One module so the check-out screen, the account page, the history rows and the
POST handler cannot disagree about which classes are still waiting for an answer
or what the choices are called. Same reason `booking_block_reason` exists.

The two windows here are different on purpose:

- **We nudge for three days.** After that the memory is a guess, and a card that
  never clears is a card members learn to look past.
- **Rating never closes.** A class that fell out of the nudge window can still be
  rated from the history rows, forever. Nothing expires quietly: the prompt goes
  away, the door does not.
"""

from datetime import timedelta

from django.utils import timezone

from .models import ClassInstance, ClassReview, class_end_at

# How far back the prompt reaches. Three days covers a member who trained Friday
# evening and next opens the site on Sunday.
REVIEW_PROMPT_DAYS = 3

# The three faces. Order is the order they are drawn in, worst to best.
FACES = [
    {
        "value": ClassReview.KURANG,
        "label": "Kurang",
        "icon": "fa-face-frown",
        "tone": "kurang",
    },
    {
        "value": ClassReview.OKE,
        "label": "Oke",
        "icon": "fa-face-meh",
        "tone": "oke",
    },
    {
        "value": ClassReview.MANTAP,
        "label": "Mantap",
        "icon": "fa-face-grin-stars",
        "tone": "mantap",
    },
]

# The second tap. Not a rating: a class can be great and still too heavy, and for
# a gym where most members are training for the first time, "kok berat banget"
# is the single most useful thing they could tell us.
INTENSITY = [
    {"value": ClassReview.ENTENG, "label": "Enteng", "icon": "fa-feather"},
    {"value": ClassReview.PAS, "label": "Pas", "icon": "fa-thumbs-up"},
    {"value": ClassReview.BERAT, "label": "Berat", "icon": "fa-fire"},
]

# Chips, so saying more costs a tap instead of a sentence. Which set shows
# depends on the face: after "Kurang" the useful question is what went wrong,
# after "Oke" or "Mantap" it is what to keep doing.
TAGS_KURANG = [
    ("penuh", "Kepenuhan"),
    ("kurang_jelas", "Kurang jelas"),
    ("kecepetan", "Kecepetan"),
    ("nunggu_alat", "Nunggu alat"),
    ("kurang_lama", "Kurang lama"),
    ("mulai_telat", "Mulainya telat"),
]

TAGS_BAGUS = [
    ("pelatih", "Pelatihnya jelas"),
    ("pemula", "Pas buat pemula"),
    ("seru", "Seru"),
    ("badan_enak", "Badan jadi enak"),
    ("temen", "Ketemu temen"),
    ("waktu", "Waktunya pas"),
]

TAG_LABELS = dict(TAGS_KURANG + TAGS_BAGUS)


def tags_for(rating):
    """The chip set that goes with a face, and the question above it."""
    if rating == ClassReview.KURANG:
        return {"question": "Apa yang kurang?", "options": TAGS_KURANG}
    return {"question": "Apa yang paling enak?", "options": TAGS_BAGUS}


def clean_tags(rating, submitted):
    """Keep only codes that belong to this face, in the order they are drawn.

    A hand-crafted POST cannot write junk into the JSON column, and the admin
    dashboard can group on the codes without defending itself.
    """
    allowed = [code for code, _ in tags_for(rating)["options"]]
    chosen = set(submitted or [])
    return [code for code in allowed if code in chosen]


def thanks_line(rating):
    """What the member reads the moment their tap lands."""
    if rating == ClassReview.KURANG:
        return "Makasih, ini kami baca. Maaf kelasnya kurang."
    if rating == ClassReview.OKE:
        return "Makasih ya, udah kecatat."
    return "Makasih! Seneng dengernya."


def pending_reviews(member, now=None, days=REVIEW_PROMPT_DAYS):
    """Finished classes this member booked recently and has said nothing about.

    Newest first, so the card asks about tonight before it asks about Tuesday.
    A class the gym cancelled never happened, and a class that has not finished
    yet cannot be reviewed, which is why the end time is checked and not the
    date: at 10:00 on a Monday, that evening's booking is not a pending review.
    """
    now = now or timezone.now()
    today = timezone.localdate(now)
    instances = (
        ClassInstance.objects.filter(
            booked_members=member,
            date__gte=today - timedelta(days=days),
            date__lte=today,
        )
        .exclude(status="CANCELLED")
        .exclude(reviews__member=member)
        .select_related("class_schedule__class_obj")
        .order_by("-date", "-start_time")
    )
    return [i for i in instances if class_end_at(i) <= now]


def reviews_by_instance(member, instances):
    """{instance id: review} for rows that need to show what was already said."""
    ids = [i.id for i in instances]
    if not ids:
        return {}
    return {
        review.class_instance_id: review
        for review in ClassReview.objects.filter(
            member=member, class_instance_id__in=ids
        )
    }


def attach_reviews(member, rows, now=None, get_instance=lambda row: row):
    """Hang `review` and `can_review` on past-class rows, for the history lists.

    One query for the lot. `can_review` is what decides whether the row offers a
    link, and it is only false for a class that has not finished yet or one the
    gym cancelled, never because time ran out.
    """
    now = now or timezone.now()
    instances = [get_instance(row) for row in rows]
    reviews = reviews_by_instance(member, instances)
    for instance in instances:
        instance.review = reviews.get(instance.id)
        instance.can_review = (
            instance.status != "CANCELLED" and class_end_at(instance) <= now
        )
    return rows
