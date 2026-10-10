"""Cost accounting, token tracking, and budget ceiling guard for LLM executions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ExecutionCostRecord:
    case_id: str
    chunk_index: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    duration_seconds: float
    model_id: str


class CostTracker:
    """Tracks token consumption and enforces conservative $20.00 ceiling."""

    def __init__(
        self,
        cost_per_input_million: float = 3.00,
        cost_per_output_million: float = 15.00,
        budget_ceiling_usd: float = 20.00,
        ledger_path: Path | None = None,
    ):
        self.cost_per_input_million = cost_per_input_million
        self.cost_per_output_million = cost_per_output_million
        self.budget_ceiling_usd = budget_ceiling_usd
        self.ledger_path = ledger_path
        self.records: list[ExecutionCostRecord] = []

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate USD cost given prompt and completion tokens."""
        in_cost = (prompt_tokens / 1_000_000.0) * self.cost_per_input_million
        out_cost = (completion_tokens / 1_000_000.0) * self.cost_per_output_million
        return round(in_cost + out_cost, 6)

    def total_cost(self) -> float:
        """Return aggregate USD cost accumulated so far."""
        return sum(r.cost_usd for r in self.records)

    def would_exceed_ceiling(self, reserved_prompt_tokens: int, reserved_completion_tokens: int) -> bool:
        """Check if an impending request would breach the budget ceiling."""
        projected = self.calculate_cost(reserved_prompt_tokens, reserved_completion_tokens)
        return (self.total_cost() + projected) > self.budget_ceiling_usd

    def record_usage(
        self,
        case_id: str,
        chunk_index: int,
        prompt_tokens: int,
        completion_tokens: int,
        duration_seconds: float,
        model_id: str,
    ) -> ExecutionCostRecord:
        """Record usage and save to persistent ledger if configured."""
        cost = self.calculate_cost(prompt_tokens, completion_tokens)
        rec = ExecutionCostRecord(
            case_id=case_id,
            chunk_index=chunk_index,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost,
            duration_seconds=round(duration_seconds, 3),
            model_id=model_id,
        )
        self.records.append(rec)

        if self.ledger_path:
            self._save_ledger()

        return rec

    def _save_ledger(self) -> None:
        if self.ledger_path is None:
            return
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "budget_ceiling_usd": self.budget_ceiling_usd,
            "total_cost_usd": round(self.total_cost(), 4),
            "total_records": len(self.records),
            "records": [asdict(r) for r in self.records],
        }
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
