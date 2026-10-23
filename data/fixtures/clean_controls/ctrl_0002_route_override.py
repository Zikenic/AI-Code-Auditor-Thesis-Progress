"""Clean Control Fixture: CTRL-0002
Paired with: CAND-0002 (Category 1: Boundary / Logic / Control Flow)
Target Scope: Routing dependency resolution and dependency override mapping
Intended Behavior: Resolves endpoint dependencies with explicit fallback to base provider
when override is not present, correctly guarding against unhandled routes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class DependencyResolver:
    """Manages route dependency resolution with optional testing overrides."""

    def __init__(self) -> None:
        self._overrides: dict[Callable[..., Any], Callable[..., Any]] = {}

    def set_override(self, original: Callable[..., Any], replacement: Callable[..., Any]) -> None:
        """Register a replacement callable for a declared dependency."""
        self._overrides[original] = replacement

    def clear_override(self, original: Callable[..., Any]) -> None:
        """Remove a previously registered override if present."""
        self._overrides.pop(original, None)

    def resolve(self, dependency: Callable[..., Any]) -> Callable[..., Any]:
        """Return the registered override if configured, otherwise the original provider."""
        if dependency in self._overrides:
            return self._overrides[dependency]
        return dependency
