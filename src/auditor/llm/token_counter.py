"""Token counter client connecting to the provider-supported messages/count_tokens endpoint.

Ensures:
- Strict token counting using official API endpoint before any benchmark call.
- Zero heuristic approximation or character-density guessing for official measurements.
- Explicit provenance tracking for token counting methods.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from auditor.llm.credentials import GatewayCredentials, load_gateway_credentials


class TokenCounterError(RuntimeError):
    """Raised when token counting communication or parsing fails."""

    pass


@dataclass(frozen=True)
class TokenCountResult:
    """Detailed token counting result with explicit method provenance."""

    input_tokens: int
    method: str  # e.g., "gateway_messages_count_tokens", "mock_tokenizer", "heuristic_fallback"
    is_heuristic: bool = False
    model_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ITokenCounter(Protocol):
    """Protocol for token counting implementations."""

    def count_tokens(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> int:
        """Count input tokens for user content and optional system prompt."""
        ...

    def count_source_tokens(self, text: str) -> int:
        """Convenience method for counting raw or rendered source code tokens."""
        ...


class ApiTokenCounter:
    """Official API token counter utilizing /v1/messages/count_tokens."""

    def __init__(self, credentials: GatewayCredentials, model_id: str | None = None, timeout: float = 30.0):
        self.credentials = credentials
        self.model_id = model_id or credentials.model_id
        self.timeout = timeout
        self.endpoint_url = f"{credentials.base_url}/v1/messages/count_tokens"

    def count_detailed(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> TokenCountResult:
        """Count tokens accurately via provider /v1/messages/count_tokens with detailed provenance."""
        if not user_content and not system_prompt:
            return TokenCountResult(
                input_tokens=0,
                method="gateway_messages_count_tokens",
                is_heuristic=False,
                model_id=self.model_id,
                details={"reason": "empty_content"},
            )

        tokens = self.count_tokens(
            user_content=user_content,
            system_prompt=system_prompt,
            thinking_type=thinking_type,
            thinking_effort=thinking_effort,
        )
        return TokenCountResult(
            input_tokens=tokens,
            method="gateway_messages_count_tokens",
            is_heuristic=False,
            model_id=self.model_id,
            details={
                "has_system_prompt": bool(system_prompt),
                "thinking_type": thinking_type,
                "thinking_effort": thinking_effort,
            },
        )

    def count_full_request(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
        repo_context_tokens: int | None = None,
    ) -> TokenCountResult:
        """Submit the complete rendered prompt for exact token counting in a single API call.

        Guarantees:
        1. Exact message-level tokenization: system instructions, user query, target code,
           static findings, and repository context are measured together, capturing framing overhead.
        2. Distinguishes full-request input tokens from repository-context-only tokens.
        """
        total = self.count_tokens(
            user_content=user_content,
            system_prompt=system_prompt,
            thinking_type=thinking_type,
            thinking_effort=thinking_effort,
        )
        details: dict[str, Any] = {
            "has_system_prompt": bool(system_prompt),
            "thinking_type": thinking_type,
            "thinking_effort": thinking_effort,
        }
        if repo_context_tokens is not None:
            details["repo_context_tokens"] = repo_context_tokens
            details["prompt_excluding_context_approx"] = max(0, total - repo_context_tokens)

        return TokenCountResult(
            input_tokens=total,
            method="gateway_messages_count_tokens",
            is_heuristic=False,
            model_id=self.model_id,
            details=details,
        )

    def count_tokens(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> int:
        """Count tokens accurately via provider /v1/messages/count_tokens."""
        if not user_content and not system_prompt:
            return 0

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
                    raise TokenCounterError(f"Invalid response from count_tokens endpoint: {res_body}")
                return int(data["input_tokens"])
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            raise TokenCounterError(f"API count_tokens request failed (HTTP {e.code}): {err_msg}") from e
        except TokenCounterError:
            raise
        except Exception as e:
            raise TokenCounterError(f"Failed to communicate with token counting endpoint: {str(e)}") from e

    def count_source_tokens(self, text: str) -> int:
        """Convenience method satisfying Callable[[str], int] for SourceChunker."""
        return self.count_tokens(user_content=text)

    def __call__(self, text: str) -> int:
        """Allow ApiTokenCounter to be passed directly as a token counter callable."""
        return self.count_source_tokens(text)


class MockTokenCounter:
    """Deterministic token counter for offline testing and ablation tests.

    Explicitly marked as mock/heuristic to prevent masquerading as genuine measurements.
    """

    def __init__(self, chars_per_token: float = 3.5, words_multiplier: float = 1.25):
        self.chars_per_token = chars_per_token
        self.words_multiplier = words_multiplier

    def count_tokens(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> int:
        full_text = (system_prompt or "") + (" " if system_prompt and user_content else "") + user_content
        return self.count_source_tokens(full_text)

    def count_source_tokens(self, text: str) -> int:
        if not text:
            return 0
        by_chars = int(len(text) / self.chars_per_token) + 1
        by_words = int(len(text.split()) * self.words_multiplier) + 1
        return max(by_chars, by_words)

    def count_detailed(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> TokenCountResult:
        tokens = self.count_tokens(user_content, system_prompt, thinking_type, thinking_effort)
        return TokenCountResult(
            input_tokens=tokens,
            method="mock_tokenizer",
            is_heuristic=True,
            model_id="mock-model",
            details={"chars_per_token": self.chars_per_token},
        )

    def __call__(self, text: str) -> int:
        return self.count_source_tokens(text)


class ApproximateTiktokenCounter:
    """Approximate offline token counter based on OpenAI's tiktoken BPE.

    CRITICAL SCIENTIFIC PROVENANCE NOTE:
    Anthropic's official guidance clarifies that tiktoken is OpenAI's tokenizer
    and is NOT an accurate or authoritative substitute for Claude model token counts.
    This counter is explicitly marked with is_heuristic=True and method="approximate_tiktoken_fallback".
    It must NEVER masquerade as a model-native count or be used as an authoritative
    hard-budget measurement in production benchmarks.
    """

    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding_name = encoding_name
        self._enc = None

    def _get_encoder(self) -> Any:
        if self._enc is None:
            try:
                import tiktoken

                self._enc = tiktoken.get_encoding(self.encoding_name)
            except Exception:
                self._enc = False
        return self._enc

    def count_tokens(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> int:
        full_text = (system_prompt or "") + ("\n" if system_prompt and user_content else "") + user_content
        return self.count_source_tokens(full_text)

    def count_source_tokens(self, text: str) -> int:
        if not text:
            return 0
        enc = self._get_encoder()
        if enc:
            return len(enc.encode(text))
        return int(len(text) / 3.2) + 1

    def count_detailed(
        self,
        user_content: str,
        system_prompt: str | None = None,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> TokenCountResult:
        tokens = self.count_tokens(user_content, system_prompt, thinking_type, thinking_effort)
        return TokenCountResult(
            input_tokens=tokens,
            method="approximate_tiktoken_fallback",
            is_heuristic=True,
            model_id=f"approximate-{self.encoding_name}",
            details={
                "warning": "Anthropic documents tiktoken as an OpenAI approximation, NOT native Claude tokenization."
            },
        )

    def __call__(self, text: str) -> int:
        return self.count_source_tokens(text)


def get_gateway_token_counter(model_id: str | None = None, timeout: float = 30.0) -> ApiTokenCounter:
    """Helper to initialize ApiTokenCounter from configured environment."""
    creds = load_gateway_credentials()
    return ApiTokenCounter(credentials=creds, model_id=model_id, timeout=timeout)
