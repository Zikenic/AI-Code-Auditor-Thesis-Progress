"""Clean Control Fixture: CTRL-0016
Paired with: CAND-0031 (Category 6: Authorization & Privilege Escalation)
Target Scope: User API authorization policy and role verification
Intended Behavior: Enforces role checks and owner identity matching before permitting
user state modification, preventing unauthorized privilege escalation (CWE-269 / CWE-863).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestUser:
    user_id: int
    is_admin: bool
    roles: frozenset[str]


def can_modify_user_profile(caller: RequestUser, target_user_id: int) -> bool:
    """Authorize profile update: only system admins or self-owners are permitted."""
    if caller.is_admin:
        return True

    if "user_admin" in caller.roles:
        return True

    return caller.user_id == target_user_id
