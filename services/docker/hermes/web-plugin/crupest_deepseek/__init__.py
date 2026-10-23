"""Register the DeepSeek web search/extract backend."""

from __future__ import annotations

from plugins.web.crupest_deepseek.provider import DeepSeekWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(DeepSeekWebSearchProvider())
