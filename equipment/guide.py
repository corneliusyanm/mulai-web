"""How Panduan Alat is arranged: the muscle groups, the starter set, the steps.

The machines themselves live in the database (admins add them in /admin). This
module decides how the guide presents them, so the list page, the body map and
the detail page all agree on the group names and their order.
"""

import re
from collections import OrderedDict

from django.utils.text import slugify

# muscle_group as admins type it -> the short label on chips and the body map.
# Listed in the order the page shows them; anything else goes after, as typed.
GROUP_LABELS = OrderedDict(
    [
        ("Kaki", "Kaki"),
        ("Dada", "Dada"),
        ("Punggung", "Punggung"),
        ("Bahu", "Bahu"),
        ("Lengan", "Lengan"),
        ("Kardio (Jantung)", "Kardio"),
        ("Macam-macam", "Macam-macam"),
    ]
)
UNGROUPED = "Lainnya"

# Mulai dari sini: five machines for somebody's first visit, in the order to try
# them. All machines, so the movement is guided, and between them they cover the
# whole body after a warm-up. Proposed from the guide itself; the coaches have
# the final say, and changing the set is editing this list.
STARTER = [
    ("treadmill", "Pemanasan dulu"),
    ("leg-press", "Kaki"),
    ("vertical-press", "Dada"),
    ("lat-pulldown", "Punggung"),
    ("multi-press", "Bahu"),
]

# How many other machines the detail page suggests from the same group.
RELATED_LIMIT = 6

# A sentence ends at . ! or ? followed by space and a capital, digit or bracket.
# "dll." mid-sentence followed by a lowercase word stays in one piece.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])")

# A first sentence that says what the machine is or trains is the intro. One
# that is already an instruction ("Posisikan kedua kaki...") is step 1.
_DESCRIBES = re.compile(r"\b(melatih|dilatih|menargetkan|dirancang|latihan|alat|mesin|platform|gerakan)\b", re.I)


def group_name(equipment):
    return equipment.muscle_group or UNGROUPED


def group_label(name):
    return GROUP_LABELS.get(name, name)


def group_id(name):
    """The anchor and filter key for a group: "Kardio (Jantung)" -> "kardio-jantung"."""
    return slugify(name) or "lainnya"


def grouped(equipments):
    """[{name, label, id, items}] in page order, only groups that have machines."""
    buckets = OrderedDict((name, []) for name in GROUP_LABELS)
    for equipment in equipments:
        buckets.setdefault(group_name(equipment), []).append(equipment)
    return [
        {"name": name, "label": group_label(name), "id": group_id(name), "items": items}
        for name, items in buckets.items()
        if items
    ]


def starter(equipments):
    """The starter set that exists in the database, in order, each with its note."""
    by_slug = {equipment.slug: equipment for equipment in equipments}
    return [
        {"equipment": by_slug[slug], "note": note, "position": position}
        for position, (slug, note) in enumerate(
            ((slug, note) for slug, note in STARTER if slug in by_slug), start=1
        )
    ]


def steps(description):
    """Split a description into an intro sentence and the steps after it.

    Written by admins as one paragraph. Standing at the machine, numbered steps
    are easier to follow than a block of text, and the first sentence is almost
    usually "what this machine is for", unless it is already an instruction, in
    which case it is step 1. Nothing is dropped: joining the intro and the steps
    gives the original sentences back. Two sentences or fewer stay a plain
    paragraph, since two steps is not a list.
    """
    text = " ".join((description or "").replace("\xa0", " ").split())
    if not text:
        return {"intro": "", "steps": []}
    sentences = [part.strip() for part in _SENTENCE_END.split(text) if part.strip()]
    if len(sentences) <= 2:
        return {"intro": " ".join(sentences), "steps": []}
    if not _DESCRIBES.search(sentences[0]):
        return {"intro": "", "steps": sentences}
    return {"intro": sentences[0], "steps": sentences[1:]}


def target_muscles(equipment):
    """detailed_muscle_group as separate chips: "Bahu Depan, Dada Atas" -> 2."""
    raw = equipment.detailed_muscle_group or ""
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    # "Kardio (Jantung)" repeated as its own detail adds nothing
    return [part for part in parts if part != equipment.muscle_group]


def seo_description(equipment):
    """The first sentence, cut to fit a search result."""
    split = steps(equipment.description)
    intro = split["intro"] or (split["steps"] or [f"Cara pakai {equipment.name} di Mulai Gym."])[0]
    return intro if len(intro) <= 155 else intro[:152].rsplit(" ", 1)[0] + "..."
