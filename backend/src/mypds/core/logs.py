"""Journaux JSON structurés, avec masquage des secrets."""

import json
import logging
import re
import sys

_SECRET = re.compile(r"(?i)(token|password|secret|authorization|api[_-]?key)([\"'=:\s]+)([^\s\"'&,]+)")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = _SECRET.sub(r"\1\2***", record.getMessage())
        data = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": msg,
        }
        if record.exc_info:
            data["exc"] = _SECRET.sub(r"\1\2***", self.formatException(record.exc_info))
        return json.dumps(data, ensure_ascii=False)


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    logging.getLogger("httpx").setLevel(logging.WARNING)
