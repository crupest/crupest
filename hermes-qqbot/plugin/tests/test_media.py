from __future__ import annotations

from pathlib import Path

import pytest
from crupest_qqbot_plugin.media import MediaFetcher, is_private_host, suffix_for, url_allowed


@pytest.mark.parametrize("host", ["127.0.0.1", "10.0.0.1", "192.168.1.1", "172.16.0.1", "::1", "169.254.1.1", "0.0.0.0"])
def test_private_hosts(host: str) -> None:
    assert is_private_host(host) is True


@pytest.mark.parametrize("host", ["8.8.8.8", "example.com", "1.1.1.1"])
def test_public_hosts(host: str) -> None:
    assert is_private_host(host) is False


def test_url_scheme_allowlist() -> None:
    assert url_allowed("https://example.com/a.jpg") is True
    assert url_allowed("http://example.com/a.jpg") is True
    assert url_allowed("file:///etc/passwd") is False
    assert url_allowed("ftp://example.com/a.jpg") is False
    assert url_allowed("https://127.0.0.1/a.jpg") is False
    assert url_allowed("https:///nohost") is False
    assert url_allowed("") is False


def test_suffix_for_content_type() -> None:
    assert suffix_for("image/jpeg") == ".jpg"
    assert suffix_for("image/png; charset=binary") == ".png"
    assert suffix_for("application/octet-stream") == ".bin"
    assert suffix_for("") == ".bin"


def test_save_creates_file(tmp_path: Path) -> None:
    fetcher = MediaFetcher(max_bytes=100, cache_dir=tmp_path)
    path = fetcher.save(b"abc", ".txt")
    assert Path(path).read_bytes() == b"abc"
    assert Path(path).parent == tmp_path


def test_save_is_unique(tmp_path: Path) -> None:
    fetcher = MediaFetcher(max_bytes=100, cache_dir=tmp_path)
    assert fetcher.save(b"a") != fetcher.save(b"a")


async def test_fetch_rejects_private_before_network(tmp_path: Path) -> None:
    fetcher = MediaFetcher(max_bytes=100, cache_dir=tmp_path)
    with pytest.raises(Exception) as excinfo:
        await fetcher.fetch("http://127.0.0.1/secret")
    assert "127.0.0.1" in str(excinfo.value)
