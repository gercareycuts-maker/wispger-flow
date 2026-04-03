"""Config persistence, history management."""

import json
import threading

from wispger_flow.constants import CFG_DIR, CFG_FILE

_cfg_lock = threading.Lock()


def load_cfg():
    """Load config from JSON file, returning {} on any error."""
    try:
        return json.loads(CFG_FILE.read_text()) if CFG_FILE.exists() else {}
    except Exception:
        return {}


def save_cfg(data):
    """Merge data into config and write to disk (thread-safe)."""
    with _cfg_lock:
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        cfg = load_cfg()
        cfg.update(data)
        CFG_FILE.write_text(json.dumps(cfg))


def load_history():
    """Load transcription history from config."""
    return load_cfg().get("history", [])


def save_history_entry(text, dur, ts):
    """Append a transcription to persistent history (cap at 200)."""
    cfg = load_cfg()
    history = cfg.get("history", [])
    history.insert(0, {"text": text, "dur": round(dur, 1), "ts": ts.isoformat()})
    history = history[:200]
    save_cfg({"history": history})


def update_history_text(ts_iso, new_text):
    """Update the text of an existing history entry by timestamp."""
    cfg = load_cfg()
    history = cfg.get("history", [])
    for entry in history:
        if entry["ts"] == ts_iso:
            entry["text"] = new_text
            break
    save_cfg({"history": history})
