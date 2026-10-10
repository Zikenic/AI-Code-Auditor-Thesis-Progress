"""Static analysis module for Configuration A (deterministic baseline)."""

from pathlib import Path

STATIC_ANALYSIS_DIR = Path(__file__).resolve().parent
RULES_DIR = STATIC_ANALYSIS_DIR / "rules"
RULESET_MANIFEST_PATH = STATIC_ANALYSIS_DIR / "ruleset_manifest.json"
SEMGREP_RULES_PATH = RULES_DIR / "semgrep" / "python_security.yaml"

from auditor.static_analysis.engine import StaticAnalysisEngine, deduplicate_static_findings  # noqa: E402
from auditor.static_analysis.mapper import FindingMapper  # noqa: E402
from auditor.static_analysis.suppression import (  # noqa: E402
    ControlledSourceWorkspace,
    neutralize_inline_suppressions,
)

__all__ = [
    "STATIC_ANALYSIS_DIR",
    "RULES_DIR",
    "RULESET_MANIFEST_PATH",
    "SEMGREP_RULES_PATH",
    "StaticAnalysisEngine",
    "FindingMapper",
    "ControlledSourceWorkspace",
    "neutralize_inline_suppressions",
    "deduplicate_static_findings",
]
