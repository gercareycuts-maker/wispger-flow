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

# -- Contraction fixes (Whisper drops apostrophes) --
_CONTRACTIONS = {
    "dont": "don't", "cant": "can't", "wont": "won't", "didnt": "didn't",
    "doesnt": "doesn't", "isnt": "isn't", "arent": "aren't", "wasnt": "wasn't",
    "werent": "weren't", "havent": "haven't", "hasnt": "hasn't", "hadnt": "hadn't",
    "wouldnt": "wouldn't", "shouldnt": "shouldn't", "couldnt": "couldn't",
    "mustnt": "mustn't", "im": "I'm", "ive": "I've", "id": "I'd",
    "youre": "you're", "youve": "you've", "youd": "you'd", "youll": "you'll",
    "hes": "he's", "shes": "she's", "thats": "that's",
    "theres": "there's", "theyre": "they're", "theyve": "they've",
    "whos": "who's", "whats": "what's", "lets": "let's",
    "weve": "we've",
}

# -- Built-in tech term corrections (Whisper lowercases everything) --
_TECH_TERMS = {
    "pytorch": "PyTorch", "numpy": "NumPy", "scipy": "SciPy",
    "javascript": "JavaScript", "typescript": "TypeScript",
    "github": "GitHub", "gitlab": "GitLab", "postgres": "PostgreSQL",
    "mongodb": "MongoDB", "kubernetes": "Kubernetes",
    "docker": "Docker", "fastapi": "FastAPI",
    "nextjs": "Next.js", "nodejs": "Node.js", "reactjs": "React.js",
    "openai": "OpenAI", "chatgpt": "ChatGPT",
    "api": "API", "apis": "APIs", "url": "URL", "urls": "URLs",
    "html": "HTML", "css": "CSS", "json": "JSON", "yaml": "YAML",
    "sql": "SQL", "http": "HTTP", "https": "HTTPS", "ssh": "SSH",
    "aws": "AWS", "gcp": "GCP", "cli": "CLI",
}

# Pre-compile contraction and tech term patterns for speed
_CONTRACTION_RE = [(re.compile(r'\b' + re.escape(k) + r'\b', re.IGNORECASE), v) for k, v in _CONTRACTIONS.items()]
_TECH_TERM_RE = [(re.compile(r'\b' + re.escape(k) + r'\b'), v) for k, v in _TECH_TERMS.items()]


def _fix_contractions(text):
    """Restore apostrophes in common contractions (dont -> don't)."""
    for pat, repl in _CONTRACTION_RE:
        text = pat.sub(repl, text)
    return text


def _fix_tech_terms(text):
    """Correct casing of common tech terms (github -> GitHub)."""
    for pat, repl in _TECH_TERM_RE:
        text = pat.sub(repl, text)
    return text


def _remove_stutters(text):
    """Remove stutters where a short fragment repeats before the full word: 's s so' -> 'so'."""
    # Only match when the prefix appears at least twice before the full word
    return re.sub(r'\b(\w{1,2})\s+(\1\s+)+(\1\w+)\b', r'\3', text, flags=re.IGNORECASE)


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
    text = _remove_stutters(text)
    text = _fix_contractions(text)
    text = _fix_tech_terms(text)
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
