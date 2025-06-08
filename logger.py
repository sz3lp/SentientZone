import logging
import hashlib
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_PATH = Path('/home/pi/sz/logs/sentientzone.log')
CHAIN_PATH = LOG_PATH.parent / 'log_chain.txt'
_FORMAT = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s - %(message)s')
_configured = False


class HashChainingHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler that appends a hash chain to each entry."""

    def __init__(self, filename: str, chain_file: Path, **kwargs) -> None:
        super().__init__(filename, **kwargs)
        self.prev_hash = ''
        self.chain_file = chain_file

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        try:
            if self.shouldRollover(record):
                self.doRollover()
            if self.stream is None:
                self.stream = self._open()
            line = self.format(record)
            digest = hashlib.sha256((self.prev_hash + line).encode()).hexdigest()
            self.prev_hash = digest
            self.stream.write(f"{line} | HASH: {digest}{self.terminator}")
            self.flush()
        except Exception:
            self.handleError(record)

    def close(self) -> None:  # type: ignore[override]
        super().close()
        try:
            self.chain_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.chain_file, 'a') as f:
                f.write(self.prev_hash + '\n')
        except Exception:
            pass


def _configure() -> None:
    global _configured
    if _configured:
        return
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = HashChainingHandler(str(LOG_PATH), CHAIN_PATH, when='midnight', backupCount=7)
    handler.setFormatter(_FORMAT)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given name after configuring logging."""
    _configure()
    return logging.getLogger(name)

