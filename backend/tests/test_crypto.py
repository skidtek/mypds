import pytest
from cryptography.exceptions import InvalidTag

from mypds.core import crypto


def test_roundtrip_and_context() -> None:
    blob = crypto.encrypt("https://cal.example/secret-token.ics", "calendar_source:1:url")
    assert b"secret-token" not in blob
    assert crypto.decrypt(blob, "calendar_source:1:url").endswith("secret-token.ics")
    with pytest.raises(InvalidTag):
        crypto.decrypt(blob, "calendar_source:2:url")  # un secret ne peut pas être déplacé
