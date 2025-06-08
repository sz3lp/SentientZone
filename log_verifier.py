import hashlib
import sys
from pathlib import Path

DEFAULT_LOG = Path('/home/pi/sz/logs/sentientzone.log')


def verify(path: Path) -> bool:
    prev = ''
    try:
        with open(path) as f:
            for idx, line in enumerate(f, 1):
                line = line.rstrip('\n')
                try:
                    content, hash_part = line.rsplit('| HASH:', 1)
                except ValueError:
                    print(f'Missing hash on line {idx}')
                    return False
                calc = hashlib.sha256((prev + content.strip()).encode()).hexdigest()
                if calc != hash_part.strip():
                    print(f'Hash mismatch at line {idx}')
                    return False
                prev = calc
    except FileNotFoundError:
        print('Log file not found')
        return False
    print('Valid log chain \u2705')
    return True


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LOG
    verify(path)


if __name__ == '__main__':
    main()
