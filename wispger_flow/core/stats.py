"""Statistics tracking, achievements data, and progress calculation."""

from datetime import datetime

from wispger_flow.core.transcription import FILLERS

# -- Achievements --
ACHIEVEMENTS = [
    ("w5000", "words", 5000, "\U0001f399", "First Words", "Everyone starts somewhere", "bronze"),
    ("w10000", "words", 10000, "\U0001f4ac", "Chatterbox", "You clearly have opinions", "silver"),
    ("w20000", "words", 20000, "\U0001f4dd", "Wordsmith", "Shakespeare is quaking", "gold"),
    ("w50000", "words", 50000, "\U0001f4da", "Novelist", "That's a short book right there", "gold"),
    ("w75000", "words", 75000, "\U0001f3c6", "Marathon Speaker", "Do you ever stop talking?", "diamond"),
    ("w150000", "words", 150000, "\U0001f30d", "War & Peace", "Tolstoy would be proud", "diamond"),
    ("t50", "txns", 50, "\U0001f3af", "Getting Started", "Welcome aboard", "bronze"),
    ("t100", "txns", 100, "\U0001f4af", "Centurion", "A hundred and counting", "silver"),
    ("t500", "txns", 500, "\u26a1", "Power User", "Keyboard? Never heard of it", "gold"),
    ("t1000", "txns", 1000, "\U0001f916", "Voice Addict", "Your keyboard is collecting dust", "diamond"),
    ("like100", "like", 100, "\U0001f644", "Like, Totally", "Are you in high school?", "roast"),
    ("um200", "um", 200, "\U0001f914", "The Thinker", "Uhhhhhhhhhhhh...", "roast"),
    ("dup15", "dupes", 15, "\U0001f99c", "Broken Record", "You said the same thing 15x", "roast"),
    ("night25", "night", 25, "\U0001f319", "Night Owl", "Go to bed already", "roast"),
    ("speed100", "speed", 10, "\U0001f407", "Speed Demon", "Slow down, auctioneer", "roast"),
    ("tiny50", "tiny", 50, "\U0001f90f", "One Word Wonder", "Could've just typed it", "roast"),
    ("long60", "long", 5, "\U0001f4d6", "Monologue King", "Sir, this is a Wendy's", "roast"),
    ("morning25", "morning", 25, "\u2615", "Morning Person", "Rise and grind", "roast"),
]

ACH_HINTS = {
    "words": "Transcribe {target:,} words to unlock this achievement",
    "txns": "Complete {target:,} transcriptions to unlock this achievement",
    "like": "Say the word 'like' {target:,} times across your transcriptions",
    "um": "Say 'um' or 'uh' {target:,} times across your transcriptions",
    "dupes": "Transcribe the same thing {target} times",
    "night": "Transcribe after midnight {target} times",
    "speed": "Transcribe 100+ words in a single recording {target} times",
    "tiny": "Transcribe just 1 word {target} times",
    "long": "Record for 30+ seconds in a single session {target} times",
    "morning": "Transcribe before 7am {target} times",
}


def default_stats():
    """Return a fresh stats dict."""
    return {
        "total_words": 0, "total_txns": 0, "total_secs": 0.0, "fillers": 0,
        "filler_breakdown": {},
        "like_count": 0, "um_count": 0, "dupes": 0, "night_count": 0,
        "speed_count": 0, "tiny_count": 0, "long_count": 0, "morning_count": 0,
        "first_use": None, "unlocked": [],
    }


def ach_progress(stats, atype, target):
    """Calculate achievement progress. Returns (progress_float, display_text)."""
    cur = {
        "words": stats["total_words"], "txns": stats["total_txns"],
        "like": stats.get("like_count", 0), "um": stats.get("um_count", 0),
        "dupes": stats.get("dupes", 0), "night": stats.get("night_count", 0),
        "speed": stats.get("speed_count", 0), "tiny": stats.get("tiny_count", 0),
        "long": stats.get("long_count", 0), "morning": stats.get("morning_count", 0),
    }.get(atype, 0)
    capped = min(cur, target)
    progress = capped / target if target else 0
    if cur >= target:
        text = f"{target:,} / {target:,}  \u2713" if atype in ("words", "txns") else "Unlocked!"
    else:
        text = f"{cur:,} / {target:,}" if atype in ("words", "txns") else f"{cur} / {target}"
    return progress, text


def update_stats(stats, text, dur, last_texts):
    """Update stats dict with a new transcription. Returns (stats, newly_unlocked, last_texts)."""
    words = text.split()
    wc = len(words)
    lw = [w.lower().strip(".,!?;:") for w in words]

    stats["total_words"] += wc
    stats["total_txns"] += 1
    stats["total_secs"] += dur

    bd = stats.get("filler_breakdown", {})
    for w in lw:
        if w in FILLERS:
            stats["fillers"] += 1
            bd[w] = bd.get(w, 0) + 1
    stats["filler_breakdown"] = bd

    stats["like_count"] = stats.get("like_count", 0) + lw.count("like")
    stats["um_count"] = stats.get("um_count", 0) + sum(1 for w in lw if w in ("um", "uh", "er", "ah"))
    if wc == 1:
        stats["tiny_count"] = stats.get("tiny_count", 0) + 1
    if wc >= 100:
        stats["speed_count"] = stats.get("speed_count", 0) + 1
    if dur >= 30:
        stats["long_count"] = stats.get("long_count", 0) + 1

    h = datetime.now().hour
    if h < 7:
        stats["morning_count"] = stats.get("morning_count", 0) + 1
    if h < 5:
        stats["night_count"] = stats.get("night_count", 0) + 1

    clean = text.strip().lower()
    if clean in last_texts:
        stats["dupes"] = stats.get("dupes", 0) + 1
    last_texts.append(clean)
    if len(last_texts) > 20:
        last_texts.pop(0)

    # Check for newly unlocked achievements
    unlocked = set(stats.get("unlocked", []))
    newly_unlocked = []
    for aid, atype, target, *rest in ACHIEVEMENTS:
        if aid not in unlocked and ach_progress(stats, atype, target)[0] >= 1.0:
            unlocked.add(aid)
            newly_unlocked.append((aid, atype, target, *rest))
    stats["unlocked"] = list(unlocked)

    return stats, newly_unlocked, last_texts
