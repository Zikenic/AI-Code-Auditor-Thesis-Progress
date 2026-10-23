"""Secure environment credential loader for local API gateway.

CRITICAL SECURITY RULES:
- Never print, log, or leak secret keys or tokens.
- Loads variables from .env.txt securely without polluting global state if not desired.
- .env.txt is strictly gitignored.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE_PATH = REPO_ROOT / ".env.txt"


@dataclass(frozen=True)
class GatewayCredentials:
    api_key: str
    base_url: str
    model_id: str


def load_gateway_credentials(env_path: Path | None = None) -> GatewayCredentials:
    """Safely load API credentials from .env.txt.

    Raises:
        FileNotFoundError: If .env.txt is missing.
        ValueError: If required keys are missing or malformed.
    """
    if env_path is not None:
        target_path = env_path
    elif (REPO_ROOT / ".env").exists():
        target_path = REPO_ROOT / ".env"
    else:
        target_path = ENV_FILE_PATH

    if not target_path.exists():
        raise FileNotFoundError(f"Credential file not found at {target_path}. Stop and verify .env or .env.txt presence.")

    # Load values without polluting os.environ unless missing
    vals = dotenv_values(target_path)

    api_key = (vals.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = (vals.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "").strip()
    model_id = (vals.get("OPEN_AI_MODEL") or os.environ.get("OPEN_AI_MODEL") or "ag/claude-sonnet-4-6").strip()
    if model_id == "ag/claude-sonnet-4.6":
        model_id = "ag/claude-sonnet-4-6"

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing or empty in .env.txt.")
    if not base_url:
        raise ValueError("OPENAI_BASE_URL is missing or empty in .env.txt.")

    # Normalize base_url to ensure proper endpoint prefixing
    clean_base_url = base_url.rstrip("/")
    if clean_base_url.endswith("/v1"):
        clean_base_url = clean_base_url[:-3]

    return GatewayCredentials(api_key=api_key, base_url=clean_base_url, model_id=model_id)
