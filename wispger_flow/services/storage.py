"""Config persistence, history management with atomic writes and debounced saves."""

import json
import os
import tempfile
import threading

from wispger_flow.constants import CFG_DIR, CFG_FILE

_lock = threading.Lock()
_pending = {}
_debounce_timer = None
_DEBOUNCE_SECS = 0.5


def load_cfg():
    """Load config from JSON file, returning {} on any error."""
    try:
        return json.loads(CFG_FILE.read_text()) if CFG_FILE.exists() else {}
    except Exception:
        # Try backup before giving up
        backup = CFG_FILE.with_suffix(".json.bak")
        try:
            if backup.exists():
                return json.loads(backup.read_text())
        except Exception:
            pass
        return {}


def _atomic_write(data):
    """Write JSON to config file atomically using temp file + rename."""
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    # Write to temp file in same directory (same filesystem for atomic rename)
    fd, tmp_path = tempfile.mkstemp(dir=CFG_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        # Keep a backup of the previous config
        if CFG_FILE.exists():
            backup = CFG_FILE.with_suffix(".json.bak")
            try:
                if backup.exists():
                    backup.unlink()
                CFG_FILE.rename(backup)
            except Exception:
                pass
        os.replace(tmp_path, str(CFG_FILE))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _flush():
    """Write pending changes to disk (called by debounce timer or flush_now)."""
    global _debounce_timer
    with _lock:
        _debounce_timer = None
        if not _pending:
            return
        cfg = load_cfg()
        cfg.update(_pending)
        _pending.clear()
        _atomic_write(cfg)


def save_cfg(data):
    """Queue data to be merged into config. Writes are debounced to coalesce rapid saves."""
    global _debounce_timer
    with _lock:
        _pending.update(data)
        if _debounce_timer is not None:
            _debounce_timer.cancel()
        _debounce_timer = threading.Timer(_DEBOUNCE_SECS, _flush)
        _debounce_timer.daemon = True
        _debounce_timer.start()


def flush_now():
    """Force an immediate write of any pending changes (call on app exit)."""
    global _debounce_timer
    with _lock:
        if _debounce_timer is not None:
            _debounce_timer.cancel()
            _debounce_timer = None
    _flush()


def load_history():
    """Load transcription history from config."""
    return load_cfg().get("history", [])


def save_history_entry(text, dur, ts):
    """Append a transcription to persistent history (cap at 200). Writes immediately."""
    with _lock:
        cfg = load_cfg()
        history = cfg.get("history", [])
        history.insert(0, {"text": text, "dur": round(dur, 1), "ts": ts.isoformat()})
        history = history[:200]
        # Merge into pending so nothing is lost, then write everything
        _pending.update({"history": history})
        cfg.update(_pending)
        _pending.clear()
        _atomic_write(cfg)


def update_history_text(ts_iso, new_text):
    """Update the text of an existing history entry by timestamp. Writes immediately."""
    with _lock:
        cfg = load_cfg()
        history = cfg.get("history", [])
        for entry in history:
            if entry["ts"] == ts_iso:
                entry["text"] = new_text
                break
        _pending.update({"history": history})
        cfg.update(_pending)
        _pending.clear()
        _atomic_write(cfg)
