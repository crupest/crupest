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
import uuid
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

_MAX_REDIRECTS = 3


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

    async def fetch(self, url: str) -> tuple[bytes, str]:
        if not url_allowed(url):
            raise UnsafeUrl(url)
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        if self._session_factory is None:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                return await self._fetch_with(session, url)
        return await self._fetch_with(self._session_factory(), url)

    async def _fetch_with(self, session, url: str) -> tuple[bytes, str]:
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
                body = bytearray()
                async for chunk in response.content.iter_chunked(64 * 1024):
                    body.extend(chunk)
                    if len(body) > self._max_bytes:
                        raise TooLarge(f"{len(body)} bytes > {self._max_bytes}")
                return bytes(body), response.headers.get("Content-Type", "")
        raise MediaError("too many redirects")

    def save(self, data: bytes, suffix: str = ".bin") -> str:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        name = f"qqbot_{uuid.uuid4().hex}{suffix}"
        path = self._cache_dir / name
        path.write_bytes(data)
        return str(path)


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
