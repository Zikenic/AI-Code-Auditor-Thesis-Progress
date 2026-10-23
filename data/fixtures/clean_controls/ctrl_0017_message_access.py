"""Clean Control Fixture: CTRL-0017
Paired with: CAND-0032 (Category 6: Authorization & Privilege Escalation)
Target Scope: Message retrieval access control and room membership validation
Intended Behavior: Checks caller membership in channel/room before returning message
content, preventing Broken Object-Level Authorization (BOLA / CWE-863 / CWE-639).
"""

from __future__ import annotations

from typing import Protocol


class ChannelMembershipService(Protocol):
    """Protocol for checking user room membership."""

    def is_user_in_channel(self, user_id: int, channel_id: int) -> bool: ...


def can_read_message(
    user_id: int,
    message_channel_id: int,
    membership_service: ChannelMembershipService,
) -> bool:
    """Authorize message reading: user must be an active member of message's channel."""
    if user_id <= 0 or message_channel_id <= 0:
        return False

    return membership_service.is_user_in_channel(user_id, message_channel_id)
