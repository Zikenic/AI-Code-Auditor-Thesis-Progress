"""Configuration B frozen execution configuration and parameter specifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ConfigBExecutionConfig:
    """Frozen parameters for Configuration B benchmark execution.

    Parameters:
    - provider: Anthropic Messages API (via direct or local gateway endpoint)
    - model_id: claude-sonnet-4-6 (gateway identifier: ag/claude-sonnet-4.6 or claude-sonnet-4-6)
    - display_name: Claude Sonnet 4.6
    - source_token_budget: 16,000 tokens (dedicated to rendered code & prefixes)
    - prompt_token_budget: 2,000 tokens (system instructions and JSON schema)
    - max_completion_tokens: 16,384 tokens (output ceiling)
    - thinking_config: {"type": "adaptive"}
    - output_config: {"effort": "medium"}
    - temperature: None (omitted)
    - budget_ceiling_usd: $8.00 (Config B allocation from $20.00 combined pool)
    - stochasticity_policy: single_stochastic_observation
    """

    provider: str = "anthropic"
    model_id: str = "claude-sonnet-4-6"
    gateway_model_id: str = "ag/claude-sonnet-4-6"
    display_name: str = "Claude Sonnet 4.6"
    source_token_budget: int = 16_000
    prompt_token_budget: int = 2_000
    max_completion_tokens: int = 16_384
    thinking_type: str = "adaptive"
    thinking_effort: str = "medium"
    temperature: float | None = None
    config_b_budget_usd: float = 8.00
    total_ceiling_usd: float = 20.00
    stochasticity_policy: Literal["single_stochastic_observation", "predeclared_repeated_trials"] = (
        "single_stochastic_observation"
    )

    # Standard Claude 3.5/Sonnet pricing baseline per million tokens ($3 / $15)
    cost_per_input_million: float = 3.00
    cost_per_output_million: float = 15.00

    @property
    def budget_ceiling_usd(self) -> float:
        """Config B allocation ceiling."""
        return self.config_b_budget_usd

    def get_thinking_payload(self) -> dict[str, Any]:
        """Return official thinking payload."""
        return {"type": self.thinking_type}

    def get_output_config_payload(self) -> dict[str, Any]:
        """Return official output config payload."""
        return {"effort": self.thinking_effort}


DEFAULT_CONFIG_B_PARAMS = ConfigBExecutionConfig()


@dataclass(frozen=True)
class ConfigCExecutionConfig:
    """Frozen parameters for Configuration C benchmark execution.

    Parameters:
    - provider: Anthropic Messages API (via local proxy gateway)
    - model_id: claude-sonnet-4-6 (gateway identifier: ag/claude-sonnet-4-6)
    - display_name: Claude Sonnet 4.6
    - source_token_budget: 16,000 tokens (dedicated to rendered code & prefixes)
    - static_token_budget: 2,000 tokens (dedicated to chunk-filtered static findings)
    - prompt_token_budget: 2,000 tokens (system instructions and JSON schema)
    - max_completion_tokens: 16,384 tokens (output ceiling)
    - thinking_config: {"type": "adaptive"}
    - output_config: {"effort": "medium"}
    - temperature: None (omitted)
    - config_c_budget_usd: $6.00 (Config C allocation)
    - total_ceiling_usd: $20.00
    - stochasticity_policy: single_stochastic_observation
    """

    provider: str = "anthropic"
    model_id: str = "claude-sonnet-4-6"
    gateway_model_id: str = "ag/claude-sonnet-4-6"
    display_name: str = "Claude Sonnet 4.6"
    source_token_budget: int = 16_000
    static_token_budget: int = 2_000
    prompt_token_budget: int = 2_000
    max_completion_tokens: int = 16_384
    thinking_type: str = "adaptive"
    thinking_effort: str = "medium"
    temperature: float | None = None
    config_c_budget_usd: float = 6.00
    total_ceiling_usd: float = 20.00
    stochasticity_policy: Literal["single_stochastic_observation", "predeclared_repeated_trials"] = (
        "single_stochastic_observation"
    )

    cost_per_input_million: float = 3.00
    cost_per_output_million: float = 15.00

    @property
    def budget_ceiling_usd(self) -> float:
        """Config C allocation ceiling."""
        return self.config_c_budget_usd


DEFAULT_CONFIG_C_PARAMS = ConfigCExecutionConfig()


@dataclass(frozen=True)
class ConfigDExecutionConfig:
    """Frozen parameters for Configuration D benchmark execution.

    Parameters:
    - provider: Anthropic Messages API (via local proxy gateway)
    - model_id: claude-sonnet-4-6 (gateway identifier: ag/claude-sonnet-4-6)
    - display_name: Claude Sonnet 4.6
    - source_token_budget: 16,000 tokens (dedicated to rendered code & prefixes)
    - static_token_budget: 2,000 tokens (dedicated to chunk-filtered static findings)
    - context_token_budget: 4,000 tokens (dedicated to repository context excerpts)
    - prompt_token_budget: 2,000 tokens (system instructions and JSON schema)
    - max_completion_tokens: 16,384 tokens (output ceiling)
    - thinking_config: {"type": "adaptive"}
    - output_config: {"effort": "medium"}
    - temperature: None (omitted)
    - config_d_budget_usd: $6.00 (Config D allocation)
    - total_ceiling_usd: $20.00
    - stochasticity_policy: single_stochastic_observation
    """

    provider: str = "anthropic"
    model_id: str = "claude-sonnet-4-6"
    gateway_model_id: str = "ag/claude-sonnet-4-6"
    display_name: str = "Claude Sonnet 4.6"
    source_token_budget: int = 16_000
    static_token_budget: int = 2_000
    context_token_budget: int = 4_000
    prompt_token_budget: int = 2_000
    max_completion_tokens: int = 16_384
    thinking_type: str = "adaptive"
    thinking_effort: str = "medium"
    temperature: float | None = None
    config_d_budget_usd: float = 6.00
    total_ceiling_usd: float = 20.00
    stochasticity_policy: Literal["single_stochastic_observation", "predeclared_repeated_trials"] = (
        "single_stochastic_observation"
    )

    cost_per_input_million: float = 3.00
    cost_per_output_million: float = 15.00

    @property
    def budget_ceiling_usd(self) -> float:
        """Config D allocation ceiling."""
        return self.config_d_budget_usd

    def get_thinking_payload(self) -> dict[str, Any]:
        """Return official thinking payload."""
        return {"type": self.thinking_type}

    def get_output_config_payload(self) -> dict[str, Any]:
        """Return official output config payload."""
        return {"effort": self.thinking_effort}


DEFAULT_CONFIG_D_PARAMS = ConfigDExecutionConfig()
