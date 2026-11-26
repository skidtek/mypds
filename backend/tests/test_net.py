import ipaddress

import pytest

from mypds.core import net
from mypds.core.settings import get_settings


@pytest.mark.parametrize(
    "ip,public",
    [
        ("8.8.8.8", True),
        ("10.0.0.1", False),
        ("192.168.1.10", False),
        ("172.16.5.5", False),
        ("127.0.0.1", False),
        ("169.254.169.254", False),
        ("100.64.1.1", False),
        ("0.0.0.0", False),
        ("::1", False),
        ("fd00::1", False),
        ("fe80::1", False),
        ("::ffff:192.168.0.1", False),
        ("2606:4700:4700::1111", True),
    ],
)
def test_is_public_ip(ip: str, public: bool) -> None:
    assert net.is_public_ip(ipaddress.ip_address(ip)) is public


async def test_blocks_private_literal() -> None:
    with pytest.raises(net.OutboundBlocked):
        await net.resolve_checked("192.168.1.10", 8006)


async def test_blocks_localhost_name() -> None:
    with pytest.raises(net.OutboundBlocked):
        await net.resolve_checked("localhost", 80)


async def test_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "outbound_allow_hosts", ["nextcloud.lan", "10.0.0.5"])
    assert str(await net.resolve_checked("10.0.0.5", 443)) == "10.0.0.5"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x.org/a", "http://user:pw@example.org/", "gopher://a"])
def test_rejects_bad_urls(url: str) -> None:
    with pytest.raises(net.OutboundError):
        net.validate_url(url)


async def test_fetch_refuses_internal_before_connecting() -> None:
    with pytest.raises(net.OutboundBlocked):
        await net.fetch("http://127.0.0.1:5432/", max_bytes=10)
