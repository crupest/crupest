"""Media download with a small SSRF guard and a bounded cache.

The plugin is the only side that touches media URLs, so the guard lives here:
scheme allowlist, no private/loopback targets, redirects re-validated, and a
hard byte cap while streaming.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

_MAX_REDIRECTS = 3

#: Local media cache retention. Old files are pruned at startup and daily.
CACHE_MAX_AGE_SECONDS = 7 * 24 * 3600
CACHE_MAX_BYTES = 1024**3


class MediaError(Exception):
    """Base class for download problems."""


class UnsafeUrl(MediaError):
    """URL scheme/host is not allowed."""


class TooLarge(MediaError):
    """Body exceeded the configured limit."""


def is_private_host(host: str) -> bool:
    """True for loopback/private/link-local/reserved/unspecified addresses."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def url_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname or ""
    if not host:
        return False
    return not is_private_host(host)


async def _host_is_public(host: str) -> bool:
    """Resolve *host* and reject if any address is private (DNS pinning)."""
    if is_private_host(host):
        return False
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    for info in infos:
        address = info[4][0]
        if is_private_host(address):
            return False
    return True


class MediaFetcher:
    def __init__(
        self,
        *,
        max_bytes: int,
        cache_dir: str | Path,
        timeout: float = 30.0,
        session_factory=None,
    ) -> None:
        self._max_bytes = max_bytes
        self._cache_dir = Path(cache_dir)
        self._timeout = timeout
        self._session_factory = session_factory

    async def fetch_to_cache(
        self, url: str, suffix_fallback: str = ".bin",
    ) -> tuple[str, str, int]:
        """Stream *url* into the cache and return ``(path, content_type, size)``."""
        if not url_allowed(url):
            raise UnsafeUrl(url)
        # ``total`` must stay unlimited: a large file can take minutes, while
        # ``sock_read`` still kills a stalled connection.
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=self._timeout)
        try:
            if self._session_factory is None:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    return await self._fetch_to_cache_with(session, url, suffix_fallback)
            async with self._session_factory() as session:
                return await self._fetch_to_cache_with(session, url, suffix_fallback)
        except MediaError:
            raise
        except (aiohttp.ClientError, TimeoutError, OSError) as exc:
            raise MediaError(str(exc)) from exc

    async def _fetch_to_cache_with(self, session, url: str, suffix_fallback: str) -> tuple[str, str, int]:
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            parsed = urlparse(current)
            if not await _host_is_public(parsed.hostname or ""):
                raise UnsafeUrl(current)
            async with session.get(current, allow_redirects=False) as response:
                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        raise MediaError(f"redirect without Location: {current}")
                    current = str(response.url.join(location))
                    if not url_allowed(current):
                        raise UnsafeUrl(current)
                    continue
                if response.status != 200:
                    raise MediaError(f"HTTP {response.status} for {current}")
                return await self._stream_to_file(response, suffix_fallback)
        raise MediaError("too many redirects")

    async def _stream_to_file(self, response, suffix_fallback: str) -> tuple[str, str, int]:
        content_type = response.headers.get("Content-Type", "")
        length = response.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > self._max_bytes:
            raise TooLarge(f"{length} bytes > {self._max_bytes}")
        suffix = suffix_for(content_type, suffix_fallback)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        name = f"chatbot_{uuid.uuid4().hex}{suffix}"
        final = self._cache_dir / name
        part = final.with_name(name + ".part")
        size = 0
        try:
            with open(part, "wb") as handle:
                async for chunk in response.content.iter_chunked(64 * 1024):
                    size += len(chunk)
                    if size > self._max_bytes:
                        raise TooLarge(f"{size} bytes > {self._max_bytes}")
                    handle.write(chunk)
            part.replace(final)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        return str(final), content_type, size

    def save(self, data: bytes, suffix: str = ".bin") -> str:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        name = f"chatbot_{uuid.uuid4().hex}{suffix}"
        path = self._cache_dir / name
        path.write_bytes(data)
        return str(path)

    def prune(
        self,
        *,
        max_age_seconds: float = CACHE_MAX_AGE_SECONDS,
        max_bytes: int = CACHE_MAX_BYTES,
    ) -> tuple[int, int]:
        """Delete cache files past the age limit, then the oldest over the size cap.

        Only regular files directly under ``cache_dir`` are touched, so the
        shared ``/opt/data/share`` tree is never modified.  Returns
        ``(removed_files, removed_bytes)``.
        """
        if not self._cache_dir.is_dir():
            return 0, 0
        now = time.time()
        removed_files = removed_bytes = 0
        kept: list[tuple[float, int, Path]] = []
        total = 0
        for path in self._cache_dir.iterdir():
            try:
                if not path.is_file():
                    continue
                stat = path.stat()
            except OSError:
                continue
            if now - stat.st_mtime > max_age_seconds:
                try:
                    path.unlink()
                except OSError:
                    continue
                removed_files += 1
                removed_bytes += stat.st_size
                continue
            kept.append((stat.st_mtime, stat.st_size, path))
            total += stat.st_size
        if total > max_bytes:
            for _, size, path in sorted(kept):
                if total <= max_bytes:
                    break
                try:
                    path.unlink()
                except OSError:
                    continue
                removed_files += 1
                removed_bytes += size
                total -= size
        return removed_files, removed_bytes


def suffix_for(content_type: str, fallback: str = ".bin") -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "audio/amr": ".amr",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "video/mp4": ".mp4",
    }
    return mapping.get((content_type or "").split(";")[0].strip().lower(), fallback)
