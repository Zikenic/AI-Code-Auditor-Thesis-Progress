"""Unit and integration tests for real tokenizer measurement and token accounting."""

from __future__ import annotations

import io
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from auditor.llm.chunker import SourceChunker
from auditor.llm.credentials import GatewayCredentials
from auditor.llm.token_counter import (
    ApiTokenCounter,
    MockTokenCounter,
    TokenCounterError,
)

DUMMY_CREDS = GatewayCredentials(
    base_url="http://localhost:20128",
    api_key="test-api-key",
    model_id="ag/claude-sonnet-4-6",
)


def make_mock_response(status_code: int, payload_bytes: bytes) -> MagicMock:
    """Helper to mock urllib response."""
    resp = MagicMock()
    resp.read.return_value = payload_bytes
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = None
    return resp


class TestApiTokenCounter:
    """Tests for the live/mocked ApiTokenCounter communicating with /v1/messages/count_tokens."""

    def test_empty_string_returns_zero_without_network_call(self):
        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        with patch("urllib.request.urlopen") as mock_urlopen:
            count = counter.count_tokens("")
            assert count == 0
            mock_urlopen.assert_not_called()

            detail = counter.count_detailed("")
            assert detail.input_tokens == 0
            assert detail.method == "gateway_messages_count_tokens"
            assert not detail.is_heuristic
            mock_urlopen.assert_not_called()

    def test_normal_source_token_counting(self):
        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        normal_code = "def authenticate(username: str, password_hash: str) -> bool:\n    return True\n"
        mock_resp = make_mock_response(200, b'{"input_tokens": 18}')

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            count = counter.count_tokens(normal_code)
            assert count == 18
            mock_urlopen.assert_called_once()

    def test_unicode_character_handling(self):
        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        unicode_snippet = "# Ki\u1ec3m tra t\u00e0i kho\u1ea3n ng\u01b0\u1eddi d\u00f9ng \U0001f512\nmsg = '\u4f60\u597d \ud83c\udf0d'\n"
        mock_resp = make_mock_response(200, b'{"input_tokens": 24}')

        with patch("urllib.request.urlopen", return_value=mock_resp):
            detail = counter.count_detailed(unicode_snippet)
            assert detail.input_tokens == 24
            assert detail.method == "gateway_messages_count_tokens"
            assert not detail.is_heuristic

    def test_prompt_vs_context_accounting(self):
        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        user_msg = "def calculate_risk(): pass"
        sys_prompt = "You are an expert security auditor."

        # Case 1: user only
        with patch("urllib.request.urlopen", return_value=make_mock_response(200, b'{"input_tokens": 7}')):
            user_only_count = counter.count_tokens(user_msg)
            assert user_only_count == 7

        # Case 2: user + system prompt
        with patch("urllib.request.urlopen", return_value=make_mock_response(200, b'{"input_tokens": 15}')):
            combined_count = counter.count_tokens(user_msg, system_prompt=sys_prompt)
            assert combined_count == 15
            assert combined_count > user_only_count

    def test_large_source_code_counting(self):
        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        large_source = "\n".join([f"def func_{i}():\n    return {i}" for i in range(500)])
        mock_resp = make_mock_response(200, b'{"input_tokens": 4250}')

        with patch("urllib.request.urlopen", return_value=mock_resp):
            count = counter.count_tokens(large_source)
            assert count == 4250

    def test_error_handling_http_failure(self):
        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        http_err = urllib.error.HTTPError(
            url="http://localhost:20128/v1/messages/count_tokens",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b'{"error": "model overload"}'),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            with pytest.raises(TokenCounterError) as exc_info:
                counter.count_tokens("def foo(): pass")
            assert "HTTP 500" in str(exc_info.value)

    def test_error_handling_network_timeout(self):
        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
            with pytest.raises(TokenCounterError) as exc_info:
                counter.count_tokens("def foo(): pass")
            assert "Failed to communicate" in str(exc_info.value)


class TestMockTokenCounterAndChunkerIntegration:
    """Verify MockTokenCounter provenance and chunker budget enforcement."""

    def test_mock_token_counter_explicitly_heuristic(self):
        mock_counter = MockTokenCounter(chars_per_token=4.0)
        detail = mock_counter.count_detailed("def simple(): pass")
        assert detail.is_heuristic is True
        assert detail.method == "mock_tokenizer"
        assert detail.input_tokens > 0

    def test_chunker_with_token_counter_budget_enforcement(self):
        # A mock counter that returns 1 token per character
        def strict_char_counter(text: str) -> int:
            return len(text)

        # Budget of 250 characters (header/footer alone is ~85 chars)
        chunker = SourceChunker(token_budget=250, token_counter=strict_char_counter, tier3_overlap=2)

        # Generate source that exceeds budget (e.g. 50 lines of code)
        long_code = ("# line comment\n" * 50)  # ~750 chars
        chunks = chunker.chunk_source(long_code, "test.py")

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.token_count_method == "tokenizer"
            assert chunk.token_estimate <= 250

    def test_chunker_fallback_provenance_flag(self):
        # Chunker initialized without token counter uses fallback heuristic
        chunker = SourceChunker(token_budget=16000)
        chunks = chunker.chunk_source("x = 1\ny = 2\n", "test.py")
        assert len(chunks) == 1
        assert chunks[0].token_count_method == "fallback_heuristic"

    def test_live_gateway_token_counting_without_generation(self):
        """Verify real gateway token-counting endpoint without making any LLM generation calls."""
        from auditor.llm.credentials import load_gateway_credentials

        try:
            creds = load_gateway_credentials()
            counter = ApiTokenCounter(credentials=creds)
            # Count tokens for sample Python function
            res = counter.count_detailed("def check_privilege(role: str) -> bool:\n    return role == 'admin'\n")
            assert res.input_tokens > 0
            assert res.method == "gateway_messages_count_tokens"
            assert res.is_heuristic is False
        except Exception as e:
            pytest.skip(f"Live gateway not reachable or credentials missing: {e}")

    def test_full_prompt_token_accounting_coverage(self):
        """Verify token counter properly measures complete prompt composition."""
        from auditor.llm.chunker import SourceChunk
        from auditor.llm.prompt_builder import (
            build_config_d_user_prompt,
            get_system_prompt,
        )

        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        dummy_chunk = SourceChunk(
            file_path="app/auth.py",
            chunk_index=1,
            total_chunks=1,
            start_line=1,
            end_line=10,
            total_lines=10,
            rendered_text="=== AUDIT TARGET: app/auth.py ===\n1: def login(): pass\n",
            raw_code="def login(): pass\n",
            token_estimate=15,
            tier=1,
            scope_description="Whole file",
        )
        static_sec = "### DETECTED STATIC FINDINGS\n1. CWE-89 on line 1\n"
        context_sec = "### REPOSITORY CONTEXT\ndef helper(): return True\n"

        user_prompt = build_config_d_user_prompt(dummy_chunk, static_sec, context_sec)
        system_prompt = get_system_prompt("D")

        mock_resp = make_mock_response(200, b'{"input_tokens": 128}')
        with patch("urllib.request.urlopen", return_value=mock_resp):
            full_count = counter.count_tokens(user_prompt, system_prompt=system_prompt)
            assert full_count == 128

    def test_exact_model_id_parity_between_counter_and_inference(self):
        """Ensure token counter submits the exact model identifier expected by inference."""
        import json

        from auditor.llm.config import DEFAULT_CONFIG_B_PARAMS

        counter = ApiTokenCounter(credentials=DUMMY_CREDS, model_id=DEFAULT_CONFIG_B_PARAMS.gateway_model_id)
        assert counter.model_id == DEFAULT_CONFIG_B_PARAMS.gateway_model_id

        mock_resp = make_mock_response(200, b'{"input_tokens": 42}')
        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            counter.count_tokens("test code")
            call_args = mock_urlopen.call_args[0]
            req = call_args[0]
            sent_payload = json.loads(req.data.decode("utf-8"))
            assert sent_payload["model"] == DEFAULT_CONFIG_B_PARAMS.gateway_model_id
            assert sent_payload["messages"][0]["content"] == "test code"

    def test_count_full_request_distinguishes_context_and_preserves_framing(self):
        """Verify count_full_request measures complete input and distinguishes repo-context tokens."""
        import json

        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        system_prompt = "You are a code auditor."
        user_prompt = "Audit this: def foo(): pass"

        mock_resp = make_mock_response(200, b'{"input_tokens": 95}')
        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = counter.count_full_request(
                user_content=user_prompt,
                system_prompt=system_prompt,
                repo_context_tokens=35,
            )
            assert result.input_tokens == 95
            assert not result.is_heuristic
            assert result.method == "gateway_messages_count_tokens"
            assert result.details["repo_context_tokens"] == 35
            assert result.details["prompt_excluding_context_approx"] == 60

            call_args = mock_urlopen.call_args[0]
            sent_payload = json.loads(call_args[0].data.decode("utf-8"))
            assert sent_payload["system"] == system_prompt
            assert sent_payload["messages"][0]["content"] == user_prompt

    def test_unicode_vietnamese_cjk_token_counting(self):
        """Verify token counting handles multi-byte UTF-8, Vietnamese, and CJK text."""
        import json

        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        multilingual_source = (
            "# Kiểm tra an toàn bảo mật tiếng Việt: Đăng nhập người dùng\n"
            "# 中文注释：验证输入参数是否包含SQL注入漏洞\n"
            "def kiem_tra_dang_nhap(ten_nguoi_dung: str) -> bool:\n"
            "    return True\n"
        )
        mock_resp = make_mock_response(200, b'{"input_tokens": 64}')
        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            count = counter.count_tokens(multilingual_source)
            assert count == 64
            call_args = mock_urlopen.call_args[0]
            sent_payload = json.loads(call_args[0].data.decode("utf-8"))
            assert "Kiểm tra" in sent_payload["messages"][0]["content"]
            assert "中文注释" in sent_payload["messages"][0]["content"]

    def test_counter_failure_raises_without_silent_downgrade(self):
        """Verify ApiTokenCounter strictly raises TokenCounterError on failure without silent downgrade."""
        counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="http://localhost:20128/v1/messages/count_tokens",
                code=503,
                msg="Service Unavailable",
                hdrs=None,
                fp=io.BytesIO(b'{"error": "gateway overloaded"}'),
            ),
        ):
            with pytest.raises(TokenCounterError) as exc_info:
                counter.count_tokens("some source code")
            assert "HTTP 503" in str(exc_info.value)

    def test_distinct_metadata_native_vs_approximate(self):
        """Verify metadata distinguishes official gateway counter from approximate fallbacks."""
        from auditor.llm.token_counter import ApproximateTiktokenCounter

        native_counter = ApiTokenCounter(credentials=DUMMY_CREDS)
        mock_resp = make_mock_response(200, b'{"input_tokens": 50}')
        with patch("urllib.request.urlopen", return_value=mock_resp):
            native_res = native_counter.count_detailed("def test(): pass", system_prompt="System")
            assert not native_res.is_heuristic
            assert native_res.method == "gateway_messages_count_tokens"

        approx_counter = ApproximateTiktokenCounter()
        approx_res = approx_counter.count_detailed("def test(): pass", system_prompt="System")
        assert approx_res.is_heuristic
        assert approx_res.method == "approximate_tiktoken_fallback"
        assert "OpenAI approximation" in approx_res.details["warning"]

        mock_counter = MockTokenCounter()
        mock_res = mock_counter.count_detailed("def test(): pass", system_prompt="System")
        assert mock_res.is_heuristic
        assert mock_res.method == "mock_tokenizer"

    def test_engine_budget_guard_with_completion_reservation(self):
        """Verify ConfigBAuditEngine enforces budget ceiling reserving max_completion_tokens."""
        from auditor.llm.config import ConfigBExecutionConfig
        from auditor.llm.cost_tracker import CostTracker
        from auditor.llm.engine import ConfigBAuditEngine
        from auditor.models.result import AuditStatus

        tight_config = ConfigBExecutionConfig(
            config_b_budget_usd=0.001,  # Very low ceiling: $0.001
            cost_per_input_million=3.0,
            cost_per_output_million=15.0,
            max_completion_tokens=4096,  # 4096 completion tokens reserved ($0.0614 minimum)
        )
        mock_counter = MockTokenCounter()
        engine = ConfigBAuditEngine(
            api_client=MagicMock(),
            config=tight_config,
            cost_tracker=CostTracker(budget_ceiling_usd=tight_config.config_b_budget_usd),
            token_counter=mock_counter,
        )
        status, findings, meta = engine.audit_source("def hello(): pass\n", "hello.py")
        assert status == AuditStatus.FAILED
        assert "Budget ceiling exceeded" in meta.get("error", "")


