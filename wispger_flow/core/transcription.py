"""Text cleanup pipeline, hallucination filter, and filler words."""

import re

# -- Whisper hallucination filter (common outputs on silence) --
HALLUCINATIONS = {
    "thank you", "thanks", "thank you.", "thanks.", "thank you for watching",
    "thanks for watching", "thanks for watching.", "thank you for watching.",
    "subscribe", "like and subscribe", "please subscribe",
    "bye", "bye.", "goodbye", "goodbye.", "you", "you.",
    "the end", "the end.", "",
}

FILLERS = {
    "um", "uh", "er", "ah", "like", "you know", "i mean", "sort of", "kind of",
    "basically", "actually", "literally", "honestly", "right", "well", "anyway", "so",
}

# -- Text cleanup helpers --
_VOWELS = set("aeiouAEIOU")
_CONSONANT_SOUND = {
    "one", "once", "uni", "unit", "united", "unique", "union", "university",
    "uniform", "unicorn", "universal", "use", "used", "useful", "user",
    "usual", "usually", "europe", "european", "ufo",
}
_SILENT_H_SKIP = {"have", "had", "has", "he", "her", "him", "his", "how", "here"}

_SENTENCE_STARTERS = {
    "So", "But", "However", "Also", "Then", "Now", "Well",
    "Actually", "Anyway", "Besides", "Furthermore", "Meanwhile",
    "Nevertheless", "Otherwise", "Therefore", "Instead", "Finally",
    "Basically", "Honestly", "Look", "Listen", "Hey", "Okay", "OK", "Yeah", "Yes", "No",
}
_QUESTION_STARTERS = {
    "who", "what", "where", "when", "why", "how", "is", "are", "was", "were",
    "do", "does", "did", "can", "could", "would", "should", "will", "shall",
    "have", "has", "had", "am", "isn't", "aren't", "wasn't", "weren't",
    "don't", "doesn't", "didn't", "can't", "couldn't", "wouldn't", "shouldn't",
}


def _fix_article(m):
    article, space, word = m.group(1), m.group(2), m.group(3)
    wl = word.lower()
    vowel = wl[0] in _VOWELS if wl else False
    if any(wl.startswith(x) for x in _CONSONANT_SOUND):
        vowel = False
    if wl.startswith("h") and len(wl) > 1 and wl[1] in _VOWELS and wl not in _SILENT_H_SKIP:
        vowel = True
    correct = "an" if vowel else "a"
    if article[0].isupper():
        correct = correct.capitalize()
    return correct + space + word


def _add_punctuation(text):
    """Insert periods and commas where Whisper omitted them."""
    words = text.split()
    if len(words) < 2:
        if text and text[-1].isalpha():
            text += "."
        return text

    result = [words[0]]
    since_punct = 1

    for i in range(1, len(words)):
        prev = result[-1]
        curr = words[i]
        prev_ended = prev[-1] in ".!?," if prev else False
        if prev_ended:
            since_punct = 0

        if not prev_ended and curr in _SENTENCE_STARTERS and since_punct >= 3:
            result[-1] = prev + "."
            since_punct = 0
        elif not prev_ended and curr.lower() in ("because", "although", "since", "unless", "whereas") and since_punct >= 3:
            result[-1] = prev + ","

        result.append(curr)
        since_punct += 1

    text = " ".join(result)
    if text and text[-1].isalpha():
        text += "."

    first = text.split()[0].lower().rstrip(".,!?") if text else ""
    if first in _QUESTION_STARTERS and text.endswith("."):
        text = text[:-1] + "?"

    return text


def clean_pipeline(text):
    """Full text cleanup: dedup, punctuation, capitalization, article correction."""
    words = text.split()
    for n in range(5, 1, -1):
        lower = [w.lower() for w in words]
        i = 0
        while i + 2 * n <= len(words):
            if lower[i:i + n] == lower[i + n:i + 2 * n]:
                words = words[:i + n] + words[i + 2 * n:]
                lower = lower[:i + n] + lower[i + 2 * n:]
            else:
                i += 1
    text = " ".join(words)
    text = _add_punctuation(text)
    text = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + " " + m.group(2).upper(), text)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    text = re.sub(r'\b(A|a|An|an)\b(\s+)(\w+)', _fix_article, text)
    text = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', text)
    return re.sub(r'  +', ' ', text).strip()


def prep_for_paste(text):
    """Add leading space for seamless paste at cursor."""
    if not text or text[0] in ".!?,;:'\"-":
        return text
    return " " + text


def apply_corrections(text, corrections):
    """Apply user-defined word corrections after clean_pipeline."""
    for wrong, right in corrections.items():
        text = re.sub(r'\b' + re.escape(wrong) + r'\b', right, text, flags=re.IGNORECASE)
    return text
