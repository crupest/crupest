"""DeepSeek Search & Fetch provider for Hermes web tools.

DeepSeek exposes two raw JSON APIs:

- ``POST /v1/tools/search``
- ``POST /v1/tools/fetch``

Both use the same ``DEEPSEEK_API_KEY`` as chat completions. This provider
registers itself as ``deepseek`` so Hermes can route ``web_search`` and
``web_extract`` through DeepSeek without any extra vendor key.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from agent.web_search_provider import WebSearchProvider, get_provider_env

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.deepseek.com"
_TIMEOUT = 60.0


def _base_url() -> str:
    return (get_provider_env("DEEPSEEK_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")


def _headers() -> Dict[str, str]:
    key = get_provider_env("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError(
            "DEEPSEEK_API_KEY environment variable not set. "
            "Get a key at https://platform.deepseek.com/"
        )
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = httpx.post(
        f"{_base_url()}{path}",
        headers=_headers(),
        json=payload,
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("DeepSeek web API returned a non-object response")
    return data


class DeepSeekWebSearchProvider(WebSearchProvider):
    @property
    def name(self) -> str:
        return "crupest-deepseek"

    @property
    def display_name(self) -> str:
        return "Crupest DeepSeek Search & Fetch"

    def is_available(self) -> bool:
        return bool(get_provider_env("DEEPSEEK_API_KEY"))

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        try:
            count = max(1, min(int(limit), 50))
            response = _post(
                "/v1/tools/search",
                {"query": query, "count": count, "need_content": False},
            )
            results: List[Dict[str, Any]] = []
            for index, item in enumerate(response.get("results", []) or []):
                if not isinstance(item, dict):
                    continue
                description = (
                    item.get("summary")
                    or item.get("snippet")
                    or item.get("content")
                    or ""
                )
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": description,
                        "position": index + 1,
                    }
                )
            return {"success": True, "data": {"web": results}}
        except Exception as exc:
            logger.warning("DeepSeek search failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for url in urls:
            try:
                response = _post("/v1/tools/fetch", {"url": url})
                results.append(
                    {
                        "url": url,
                        "title": response.get("title", ""),
                        "content": response.get("content", ""),
                        "raw_content": response.get("content", ""),
                        "metadata": {},
                    }
                )
            except Exception as exc:
                logger.warning("DeepSeek fetch failed for %s: %s", url, exc)
                results.append(
                    {
                        "url": url,
                        "title": "",
                        "content": "",
                        "raw_content": "",
                        "error": str(exc),
                    }
                )
        return results

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Crupest DeepSeek",
            "badge": "paid",
            "tag": "DeepSeek Search & Fetch; uses DEEPSEEK_API_KEY.",
            "env_vars": [
                {
                    "key": "DEEPSEEK_API_KEY",
                    "prompt": "DeepSeek API key",
                    "url": "https://platform.deepseek.com/api_keys",
                },
            ],
        }
