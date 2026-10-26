from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from crupest_chatbot_plugin.media import MediaFetcher, TooLarge, is_private_host, suffix_for, url_allowed


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
        await fetcher.fetch_to_cache("http://127.0.0.1/secret")
    assert "127.0.0.1" in str(excinfo.value)


class FakeContent:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def iter_chunked(self, _size: int):
        async def generate():
            for chunk in self._chunks:
                yield chunk

        return generate()


class FakeResponse:
    def __init__(self, chunks: list[bytes], headers: dict | None = None) -> None:
        self.status = 200
        self.headers = headers or {"Content-Type": "image/png"}
        self.content = FakeContent(chunks)
        self.url = "https://example.com/a.png"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    def get(self, _url: str, allow_redirects: bool = False):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


async def test_fetch_to_cache_streams_to_disk(tmp_path: Path, monkeypatch) -> None:
    async def fake_public(_host: str) -> bool:
        return True

    monkeypatch.setattr("crupest_chatbot_plugin.media._host_is_public", fake_public)
    response = FakeResponse([b"abc", b"def"])
    fetcher = MediaFetcher(
        max_bytes=100, cache_dir=tmp_path, session_factory=lambda: FakeSession(response),
    )

    path, content_type, size = await fetcher.fetch_to_cache("https://example.com/a.png")

    assert Path(path).read_bytes() == b"abcdef"
    assert Path(path).suffix == ".png"
    assert content_type == "image/png"
    assert size == 6


async def test_fetch_to_cache_cleans_up_when_too_large(tmp_path: Path, monkeypatch) -> None:
    async def fake_public(_host: str) -> bool:
        return True

    monkeypatch.setattr("crupest_chatbot_plugin.media._host_is_public", fake_public)
    response = FakeResponse([b"123", b"456"])
    fetcher = MediaFetcher(
        max_bytes=5, cache_dir=tmp_path, session_factory=lambda: FakeSession(response),
    )

    with pytest.raises(TooLarge):
        await fetcher.fetch_to_cache("https://example.com/a.png")

    assert list(tmp_path.iterdir()) == []


async def test_fetch_to_cache_rejects_oversized_content_length(tmp_path: Path, monkeypatch) -> None:
    async def fake_public(_host: str) -> bool:
        return True

    monkeypatch.setattr("crupest_chatbot_plugin.media._host_is_public", fake_public)
    response = FakeResponse([b"abc"], headers={"Content-Type": "image/png", "Content-Length": "10"})
    fetcher = MediaFetcher(
        max_bytes=5, cache_dir=tmp_path, session_factory=lambda: FakeSession(response),
    )

    with pytest.raises(TooLarge):
        await fetcher.fetch_to_cache("https://example.com/a.png")

    assert list(tmp_path.iterdir()) == []


def test_prune_removes_files_past_max_age(tmp_path: Path) -> None:
    fetcher = MediaFetcher(max_bytes=100, cache_dir=tmp_path)
    old = Path(fetcher.save(b"old", ".txt"))
    new = Path(fetcher.save(b"new", ".txt"))
    stale = time.time() - 8 * 24 * 3600
    os.utime(old, (stale, stale))

    removed, freed = fetcher.prune(max_age_seconds=7 * 24 * 3600, max_bytes=10**9)

    assert removed == 1
    assert freed == 3
    assert not old.exists()
    assert new.exists()


def test_prune_size_cap_removes_oldest_first(tmp_path: Path) -> None:
    fetcher = MediaFetcher(max_bytes=100, cache_dir=tmp_path)
    paths = []
    for index in range(3):
        path = Path(fetcher.save(b"x" * 10, ".bin"))
        moment = time.time() - (3 - index) * 60
        os.utime(path, (moment, moment))
        paths.append(path)

    removed, freed = fetcher.prune(max_age_seconds=10**9, max_bytes=15)

    assert removed == 2
    assert freed == 20
    assert not paths[0].exists()
    assert not paths[1].exists()
    assert paths[2].exists()


def test_prune_missing_directory_is_a_noop(tmp_path: Path) -> None:
    fetcher = MediaFetcher(max_bytes=100, cache_dir=tmp_path / "missing")
    assert fetcher.prune() == (0, 0)
