import json
import logging
import logging.config
import sys
from datetime import UTC, datetime
from typing import Any

from mona_core.config import settings

_RESERVED_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
)


class JsonFormatter(logging.Formatter):
    """Compact JSON formatter: one line per log entry, readable raw in
    `docker logs`, still valid JSON for Loki (`| json | level="ERROR"`)."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            # flatten traceback into the message itself instead of a
            # separate multi-line field — keeps one log line = one event
            trace = self.formatException(record.exc_info).replace("\n", " | ")
            message = f"{message} | {trace}"

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="seconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }

        # allow ad-hoc structured fields via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRS and key not in payload:
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging to emit JSON lines to stdout.

    Called once at import time below. Safe to call again (e.g. in tests).
    """
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"()": JsonFormatter},
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "json",
                },
            },
            "root": {
                "handlers": ["stdout"],
                "level": level.upper(),
            },
            "loggers": {
                # keep uvicorn/celery noise readable but routed to the same handler
                "uvicorn": {
                    "handlers": ["stdout"],
                    "level": level.upper(),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["stdout"],
                    "level": level.upper(),
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["stdout"],
                    "level": level.upper(),
                    "propagate": False,
                },
                "celery": {
                    "handlers": ["stdout"],
                    "level": level.upper(),
                    "propagate": False,
                },
            },
        }
    )


configure_logging(settings.log_level)
