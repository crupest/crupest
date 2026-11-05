"""Register the plugin platform when the tests run inside a real Hermes env."""
from __future__ import annotations

try:
    from gateway.platform_registry import PlatformEntry, platform_registry
except ImportError:  # unit tests use the local stubs
    pass
else:
    if not platform_registry.is_registered("onebot"):
        platform_registry.register(
            PlatformEntry(
                name="onebot",
                label="QQ",
                adapter_factory=lambda config: None,
                check_fn=lambda: True,
            )
        )
