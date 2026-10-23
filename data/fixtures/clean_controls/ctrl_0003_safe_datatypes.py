"""Clean Control Fixture: CTRL-0003
Paired with: CAND-0006 (Category 1: Boundary / Logic / Null Dereference)
Target Scope: Mapping data structure with safe key lookup and None-guarding
Intended Behavior: Implements dictionary-like access with explicit None checks and
KeyError handling, avoiding unhandled null dereferences.
"""

from __future__ import annotations

from typing import Any


class SafeDictionary:
    """Case-insensitive dictionary wrapper with explicit None and boundary checks."""

    def __init__(self, initial_data: dict[str, Any] | None = None) -> None:
        self._store: dict[str, Any] = {}
        if initial_data:
            for k, v in initial_data.items():
                if k is not None:
                    self._store[str(k).lower()] = v

    def get(self, key: str | None, default: Any = None) -> Any:
        """Safely retrieve value for key without raising on missing or None keys."""
        if key is None:
            return default
        return self._store.get(str(key).lower(), default)

    def set(self, key: str, value: Any) -> None:
        """Assign key-value pair, rejecting None keys explicitly."""
        if key is None:
            raise ValueError("Key cannot be None in SafeDictionary")
        self._store[str(key).lower()] = value

    def __len__(self) -> int:
        return len(self._store)
