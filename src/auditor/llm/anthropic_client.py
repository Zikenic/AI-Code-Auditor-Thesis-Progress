"""Anthropic Messages API client supporting direct Anthropic API and local gateway endpoints.

CRITICAL POLICY:
- Never print, log, or leak secret keys or tokens.
- Credentials loaded safely from .env.txt via GatewayCredentials.
- Supports Claude Sonnet 4.6 adaptive thinking:
  - thinking: {"type": "adaptive"}
  - output_config: {"effort": "medium"}
  - temperature: omitted
- Handles both standard JSON and Server-Sent Events (SSE) streaming responses transparently,
  reconstructing text deltas and usage token counts accurately.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from auditor.llm.credentials import GatewayCredentials, load_gateway_credentials
from auditor.llm.engine import ILlmApiClient


class AnthropicApiClient(ILlmApiClient):
    """Production Anthropic Messages API client for direct or gateway endpoints."""

    def __init__(
        self,
        credentials: GatewayCredentials | None = None,
        timeout: float = 180.0,
        max_retries: int = 3,
    ):
        self.credentials = credentials or load_gateway_credentials()
        self.timeout = timeout
        self.max_retries = max_retries
        self.endpoint_url = f"{self.credentials.base_url}/v1/messages"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        model_id: str,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> tuple[str, int, int]:
        """Execute generation request via /v1/messages and return (completion_text, prompt_tokens, completion_tokens)."""
        payload: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        # Adaptive thinking configuration per Phase 4A
        if thinking_type:
            payload["thinking"] = {"type": thinking_type}
        if thinking_effort:
            payload["output_config"] = {"effort": thinking_effort}

        # Temperature is strictly omitted

        headers = {
            "Authorization": f"Bearer {self.credentials.api_key}",
            "Content-Type": "application/json",
        }

        data_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(1, self.max_retries + 1):
            req = urllib.request.Request(self.endpoint_url, data=data_bytes, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_bytes = resp.read()

                    # Check if response is Server-Sent Events (SSE)
                    if resp_bytes.startswith(b"event:") or b"data: " in resp_bytes:
                        completion_text, p_tokens, c_tokens, stop_reason = self._parse_sse_stream(resp_bytes)
                    else:
                        resp_data = json.loads(resp_bytes.decode("utf-8"))
                        completion_text, p_tokens, c_tokens, stop_reason = self._parse_json_response(resp_data)

                    if stop_reason == "max_tokens":
                        raise RuntimeError(
                            f"LLM generation was truncated due to max_tokens limit (stop_reason={stop_reason})."
                        )

                    return completion_text, p_tokens, c_tokens

            except urllib.error.HTTPError as e:
                err_content = e.read().decode("utf-8", errors="replace")
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(2**attempt * 2)
                    continue
                raise RuntimeError(f"HTTP error {e.code} during LLM generation: {err_content}") from e
            except urllib.error.URLError as e:
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise RuntimeError(f"Connection error during LLM generation: {str(e)}") from e
            except Exception:
                raise

        raise RuntimeError("Exceeded maximum retries calling Messages API.")

    def _parse_json_response(self, resp_data: dict[str, Any]) -> tuple[str, int, int, str]:
        """Parse standard Anthropic or OpenAI-compatible JSON message response."""
        # 1. Anthropic messages format
        if "content" in resp_data:
            content_blocks = resp_data.get("content", [])
            text_parts: list[str] = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif hasattr(block, "text"):
                    text_parts.append(block.text)

            completion_text = "\n".join(text_parts).strip()
            usage = resp_data.get("usage", {})
            p_tokens = int(usage.get("input_tokens", 0))
            c_tokens = int(usage.get("output_tokens", 0))
            stop_reason = str(resp_data.get("stop_reason", "end_turn"))
            return completion_text, p_tokens, c_tokens, stop_reason

        # 2. OpenAI chat completion format
        if "choices" in resp_data:
            choices = resp_data.get("choices", [])
            msg = choices[0].get("message", {}) if choices else {}
            completion_text = str(msg.get("content", "")).strip()
            usage = resp_data.get("usage", {})
            p_tokens = int(usage.get("prompt_tokens", 0))
            c_tokens = int(usage.get("completion_tokens", 0))
            stop_reason = str(choices[0].get("finish_reason", "stop")) if choices else "stop"
            return completion_text, p_tokens, c_tokens, stop_reason

        raise ValueError(f"Unrecognized response payload structure: {list(resp_data.keys())}")

    def _parse_sse_stream(self, raw_bytes: bytes) -> tuple[str, int, int, str]:
        """Parse Server-Sent Events (SSE) byte stream into text, tokens, and stop reason."""
        lines = raw_bytes.splitlines()
        text_accum: list[str] = []
        p_tokens = 0
        c_tokens = 0
        stop_reason = "end_turn"

        for line in lines:
            line_str = line.decode("utf-8", errors="replace").strip()
            if not line_str.startswith("data: "):
                continue

            data_payload = line_str[6:].strip()
            if not data_payload or data_payload == "[DONE]":
                continue

            try:
                event = json.loads(data_payload)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")

            # Content block delta
            if event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text_accum.append(delta.get("text", ""))

            # Message delta contains final usage and stop_reason
            elif event_type == "message_delta":
                delta = event.get("delta", {})
                if "stop_reason" in delta and delta["stop_reason"]:
                    stop_reason = str(delta["stop_reason"])
                usage = event.get("usage", {})
                if "input_tokens" in usage:
                    p_tokens = int(usage["input_tokens"])
                if "output_tokens" in usage:
                    c_tokens = int(usage["output_tokens"])

            # Message start may contain initial input tokens
            elif event_type == "message_start":
                msg = event.get("message", {})
                usage = msg.get("usage", {})
                if "input_tokens" in usage and p_tokens == 0:
                    p_tokens = int(usage["input_tokens"])

        completion_text = "".join(text_accum).strip()
        return completion_text, p_tokens, c_tokens, stop_reason
