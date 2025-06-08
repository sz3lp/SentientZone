import json
import hashlib
import sys
from pathlib import Path

DEFAULT_PATH = Path('/home/pi/sz/logs/override_log.jsonl')


def verify(path: Path) -> bool:
    prev = ''
    try:
        with open(path) as f:
            for idx, line in enumerate(f, 1):
                obj = json.loads(line)
                core = {
                    'timestamp': obj['timestamp'],
                    'mode': obj['mode'],
                    'duration_minutes': obj['duration_minutes'],
                    'source': obj['source'],
                    'initiated_by': obj['initiated_by'],
                }
                calc = hashlib.sha256((json.dumps(core, sort_keys=True) + prev).encode()).hexdigest()
                if calc != obj.get('hash'):
                    print(f'Hash mismatch at line {idx}')
                    return False
                prev = obj['hash']
    except FileNotFoundError:
        print('Audit file not found')
        return False
    print('Valid audit trail \u2705')
    return True


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    verify(path)


if __name__ == '__main__':
    main()
