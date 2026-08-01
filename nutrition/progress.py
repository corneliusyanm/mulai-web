"""Where a member is up to in Belajar Gizi.

Its own module so the account page can show progress without importing views.
"""

from . import content
from .models import ChapterProgress


def by_chapter(member):
    """{chapter slug: ChapterProgress} for a member, or {} for a guest."""
    if not member:
        return {}
    return {
        row.chapter_slug: row
        for row in ChapterProgress.objects.filter(member=member)
    }


def summary(member):
    """Level, how far along, and which chapter to continue with."""
    done = by_chapter(member)
    slugs = [chapter["slug"] for chapter in content.CHAPTERS]
    finished = [slug for slug in slugs if slug in done]
    remaining = [slug for slug in slugs if slug not in done]

    # Where "Lanjut" points: the first unfinished chapter, or the first one
    # again once everything is done (rereading is fine, and the button should
    # never be dead).
    up_next = content.get_chapter(remaining[0] if remaining else slugs[0])

    return {
        "finished_count": len(finished),
        "total_chapters": len(slugs),
        "percent": round(len(finished) * 100 / len(slugs)) if slugs else 0,
        "level": content.level_name(len(finished)),
        "all_done": not remaining,
        "up_next": up_next,
        "by_chapter": done,
    }
