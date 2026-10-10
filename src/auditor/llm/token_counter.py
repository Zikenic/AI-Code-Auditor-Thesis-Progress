"""Token counter client connecting to the provider-supported messages/count_tokens endpoint.

Ensures:
- Strict token counting using official API endpoint before any benchmark call.
- Zero heuristic approximation or character-density guessing.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from auditor.llm.credentials import GatewayCredentials


class ApiTokenCounter:
    """Official API token counter utilizing /v1/messages/count_tokens."""

    def __init__(self, credentials: GatewayCredentials, model_id: str | None = None, timeout: float = 30.0):
        self.credentials = credentials
        self.model_id = model_id or credentials.model_id
        self.timeout = timeout
        self.endpoint_url = f"{credentials.base_url}/v1/messages/count_tokens"

    def count_tokens(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> int:
        """Count tokens accurately via provider /v1/messages/count_tokens."""
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": user_content}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        if thinking_type:
            payload["thinking"] = {"type": thinking_type}
        if thinking_effort:
            payload["output_config"] = {"effort": thinking_effort}

        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.credentials.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                res_body = response.read().decode("utf-8")
                data = json.loads(res_body)
                if "input_tokens" not in data:
                    raise ValueError(f"Invalid response from count_tokens endpoint: {res_body}")
                return int(data["input_tokens"])
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"API count_tokens request failed (HTTP {e.code}): {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to communicate with token counting endpoint: {str(e)}") from e
