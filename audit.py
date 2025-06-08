import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path('/home/pi/sz/logs/override_log.jsonl')


def _get_last_hash() -> str:
    if not LOG_PATH.exists():
        return ""
    try:
        with open(LOG_PATH, 'rb') as f:
            f.seek(0, 2)
            if f.tell() == 0:
                return ""
            pos = f.tell() - 1
            while pos > 0:
                f.seek(pos)
                if f.read(1) == b'\n':
                    break
                pos -= 1
            if pos <= 0:
                f.seek(0)
            line = f.readline().decode().strip()
        if line:
            return json.loads(line).get('hash', '')
    except Exception:
        return ""
    return ""


def log_override(mode: str, duration_minutes: int, source: str, initiated_by: str) -> None:
    """Append an override event to the audit log with hash chaining."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    prev = _get_last_hash()
    event = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'mode': mode,
        'duration_minutes': duration_minutes,
        'source': source,
        'initiated_by': initiated_by,
    }
    plain = json.dumps(event, sort_keys=True)
    event['hash'] = hashlib.sha256((plain + prev).encode()).hexdigest()
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(event) + '\n')

