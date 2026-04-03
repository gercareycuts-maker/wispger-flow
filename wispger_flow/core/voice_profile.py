"""Voice profile: vocabulary tracking, phrase detection, corrections, prompt building."""

from wispger_flow.core.transcription import FILLERS
from wispger_flow.constants import WHISPER_PROMPT

COMMON_WORDS = frozenset(
    "a about after again all also am an and any are as at back be because been before being below between both but by "
    "came can come could day did do does done down each even few first for from get go going good got great had has have "
    "he her here him his how i if in into is it its just know last let like long look made make many may me might more "
    "most much must my new no nor not now of off on one only or other our out over own part per put quite really right "
    "said same say see she should show side since so some something still such take tell than that the their them then "
    "there these they thing think this those through time to too two under up upon us use used using very want was way "
    "we well were what when where which while who why will with without word work would year yes yet you your "
    "able above actually against ago ahead almost already although always among another "
    "around away bad began begin behind believe best better big bit bring brought called certain "
    "change children city close company country course cut different doing door early end enough ever every "
    "example face fact family far feel felt find found four full gave give given goes gone group hand "
    "head hear help high home house however important keep kind knew large later least left less life "
    "line little live looked making man men mind money morning move mr mrs never next night nothing "
    "number often old once open order place play point possible power probably problem ran read real "
    "room run saw school second set several shall short small started state stop story sure system "
    "taken talk thought three together told took top turn water whole world write young".split()
)


def default_voice_profile():
    """Return a fresh voice profile dict."""
    return {"vocab": {}, "phrases": {}, "corrections": {}, "style_notes": "", "prompt_override": ""}


def update_voice_profile(vp, text, total_txns):
    """Update voice profile with words/phrases from a transcription. Returns updated vp."""
    words = [w.lower().strip(".,!?;:\"'") for w in text.split() if len(w) > 1]

    # Update vocab — only uncommon words
    vocab = vp.get("vocab", {})
    for w in words:
        if w not in COMMON_WORDS and w not in FILLERS:
            vocab[w] = vocab.get(w, 0) + 1
    if len(vocab) > 200:
        vocab = dict(sorted(vocab.items(), key=lambda x: -x[1])[:200])
    vp["vocab"] = vocab

    # Update phrases — bigrams and trigrams
    phrases = vp.get("phrases", {})
    for n in (2, 3):
        for i in range(len(words) - n + 1):
            ngram = words[i:i + n]
            if any(w not in COMMON_WORDS and w not in FILLERS for w in ngram):
                phrase = " ".join(ngram)
                phrases[phrase] = phrases.get(phrase, 0) + 1
    phrases = {k: v for k, v in phrases.items() if v >= 2}
    if len(phrases) > 100:
        phrases = dict(sorted(phrases.items(), key=lambda x: -x[1])[:100])
    vp["phrases"] = phrases

    # Decay every 50 transcriptions
    if total_txns > 0 and total_txns % 75 == 0:
        for d in (vp["vocab"], vp["phrases"]):
            for k in list(d):
                d[k] = round(d[k] * 0.9, 1)
                if d[k] < 1:
                    del d[k]

    return vp


def build_whisper_prompt(vp):
    """Build a Whisper prompt from the voice profile. Returns prompt string."""
    if vp.get("prompt_override", "").strip():
        return vp["prompt_override"][:600]

    parts = []
    notes = vp.get("style_notes", "").strip()
    if notes:
        parts.append(notes[:200])

    corrections = vp.get("corrections", {})
    if corrections:
        parts.append(", ".join(corrections.values())[:100])

    vocab = vp.get("vocab", {})
    if vocab:
        top = sorted(vocab.items(), key=lambda x: -x[1])[:25]
        parts.append(", ".join(w for w, _ in top))

    phrases = vp.get("phrases", {})
    if phrases:
        top = sorted(phrases.items(), key=lambda x: -x[1])[:8]
        parts.append(". ".join(p for p, _ in top))

    prompt = ". ".join(parts) if parts else WHISPER_PROMPT
    words = prompt.split()
    if len(words) > 150:
        prompt = " ".join(words[:150])
    return prompt
