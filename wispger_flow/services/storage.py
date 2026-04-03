"""Config persistence, history management with debounced writes."""

import json
import threading

from wispger_flow.constants import CFG_DIR, CFG_FILE

_cfg_lock = threading.Lock()
_pending = {}
_debounce_timer = None
_DEBOUNCE_SECS = 0.5


def load_cfg():
    """Load config from JSON file, returning {} on any error."""
    try:
        return json.loads(CFG_FILE.read_text()) if CFG_FILE.exists() else {}
    except Exception:
        return {}


def _flush():
    """Write pending changes to disk (called by debounce timer)."""
    global _debounce_timer
    with _cfg_lock:
        _debounce_timer = None
        if not _pending:
            return
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        cfg = load_cfg()
        cfg.update(_pending)
        _pending.clear()
        CFG_FILE.write_text(json.dumps(cfg))


def save_cfg(data):
    """Queue data to be merged into config. Writes are debounced to coalesce rapid saves."""
    global _debounce_timer
    with _cfg_lock:
        _pending.update(data)
        if _debounce_timer is not None:
            _debounce_timer.cancel()
        _debounce_timer = threading.Timer(_DEBOUNCE_SECS, _flush)
        _debounce_timer.daemon = True
        _debounce_timer.start()


def flush_now():
    """Force an immediate write of any pending changes (call on app exit)."""
    global _debounce_timer
    with _cfg_lock:
        if _debounce_timer is not None:
            _debounce_timer.cancel()
            _debounce_timer = None
    _flush()


def load_history():
    """Load transcription history from config."""
    return load_cfg().get("history", [])


def save_history_entry(text, dur, ts):
    """Append a transcription to persistent history (cap at 200)."""
    with _cfg_lock:
        cfg = load_cfg()
        history = cfg.get("history", [])
        history.insert(0, {"text": text, "dur": round(dur, 1), "ts": ts.isoformat()})
        history = history[:200]
    # History writes go through immediately (important data)
    _pending.update({"history": history})
    _flush()


def update_history_text(ts_iso, new_text):
    """Update the text of an existing history entry by timestamp."""
    with _cfg_lock:
        cfg = load_cfg()
        history = cfg.get("history", [])
        for entry in history:
            if entry["ts"] == ts_iso:
                entry["text"] = new_text
                break
    _pending.update({"history": history})
    _flush()
