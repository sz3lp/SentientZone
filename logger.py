import logging
import hashlib
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

def _paths() -> tuple[Path, Path, Path]:
    """Return base, log and chain paths based on environment."""
    base = Path(os.environ.get("SZ_BASE_DIR", "/home/pi/sz"))
    log = base / "logs" / "sentientzone.log"
    chain = log.parent / "log_chain.txt"
    return base, log, chain

BASE_DIR, LOG_PATH, CHAIN_PATH = _paths()
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
    global _configured, BASE_DIR, LOG_PATH, CHAIN_PATH
    if _configured:
        return
    BASE_DIR, LOG_PATH, CHAIN_PATH = _paths()
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

