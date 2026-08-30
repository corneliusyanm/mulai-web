"""Spread the daily rotation across topics instead of marching through them.

`daily_questions.py` is grouped by topic so a human can review a hundred of them,
and the rotation used to walk that file in order. One question a day turns each
group into a run: twelve straight days of calories, then twelve of protein, then
ten of drinks, with weight training not due until day 55. Members said it reads
like the same question every morning, and they were right.

Two things have to be true, and only the first is obvious:

- **No two days in a row share a topic.**
- **Every topic is spread over the whole run**, not just kept off its own heels.
  The first cut of this picked whichever topic had the most left, which never
  repeats itself but front-loads: the biggest topic took six of the first eleven
  days, and "why is it always about getting old" is the same complaint again in a
  different shape. So each topic is dealt out at an even stride instead, and a
  repair pass afterwards fixes the few places two land together.

Each topic starts at its own hashed offset, so two topics of the same size do not
march in lockstep, and the questions inside a topic are scattered rather than kept
in written order, where consecutive ones tend to be about the same food.

Hashes rather than `random`, for the same reason as `shuffle.py`: the order has to
come out identical on every machine and every deploy, forever, and a seeded RNG is
only promised to be stable within one Python version.
"""

from hashlib import md5

# Mixed into every hash. Fixed forever: changing it reshuffles the rotation, which
# is only harmless for questions nobody has been shown yet.
SALT = "mulai-gizi-topics-2026-8"


def _rank(*parts):
    return md5(":".join(parts).encode()).hexdigest()


def _fraction(*parts):
    """A stable number in [0, 1) from the same hash, for a topic's phase."""
    return int(_rank(*parts)[:8], 16) / 0x100000000


def _repair(order, topic_of, after):
    """Swap apart the few neighbours the stride left sharing a topic.

    Swapping forward rather than shifting everything keeps the even spread: an
    item moves a place or two, not to the end of the run.
    """
    for index, code in enumerate(order):
        previous = topic_of[order[index - 1]] if index else after
        if topic_of[code] != previous:
            continue
        for other in range(index + 1, len(order)):
            topic = topic_of[order[other]]
            if topic == previous:
                continue
            # The swap has to leave the other end tidy as well.
            if topic_of[order[other - 1]] == topic_of[code] and other - 1 != index:
                continue
            if other + 1 < len(order) and topic_of[order[other + 1]] == topic_of[code]:
                continue
            order[index], order[other] = order[other], order[index]
            break
    return order


def interleave_topics(codes, topic_of, after=None):
    """Return `codes` reordered so consecutive entries come from different topics.

    `topic_of` maps a code to its topic. `after` is the topic of whatever comes
    immediately before this run, so the first pick does not repeat it: the unshown
    tail of the rotation gets reordered while the days already spent stay put, and
    the join between the two should not land two drinks questions together.
    """
    buckets = {}
    for code in codes:
        buckets.setdefault(topic_of[code], []).append(code)

    placed = []
    for topic, bucket in buckets.items():
        bucket.sort(key=lambda code: _rank(SALT, code))
        phase = _fraction(SALT, topic)
        for index, code in enumerate(bucket):
            placed.append(((index + phase) / len(bucket), _rank(SALT, code), code))

    placed.sort()
    return _repair([code for _, _, code in placed], topic_of, after)
