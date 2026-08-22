"""
parity_report.py — Aggregation and rendering of multi-tier parity results.

A ParityReport collects the results from all active tiers (T1–T4) and produces
a structured summary that is stored in RosettaState and exposed via the parity
endpoint. The report explicitly labels the oracle provenance so it is clear
whether parity evidence came from hand-authored golden files, property tests,
or (in future) a live Java execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class TierResult:
    """Result of a single validation tier."""
    tier: str             # e.g. "T1_formula_completeness"
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    feedback: str = ""
    status: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "passed": self.passed,
            "feedback": self.feedback,
            "details": self.details,
            "status": self.status,
        }


@dataclass
class ParityReport:
    """
    Aggregated parity evidence from T1–T4 tiers.

    Stored in state["parity_report"] after validation and exposed via the
    GET /parity/{method} endpoint.
    """
    method: str
    baseline_mode: str     # "provisional" | "approved" | "golden_file" | "java_executed"
    overall_passed: bool
    tiers: list[TierResult] = field(default_factory=list)

    # Counts for quick display
    @property
    def tiers_passed(self) -> int:
        return sum(1 for t in self.tiers if t.passed and t.status not in ("superseded", "not_applicable"))

    @property
    def tiers_total(self) -> int:
        return sum(1 for t in self.tiers if t.status not in ("superseded", "not_applicable"))

    @property
    def tiers_superseded(self) -> int:
        return sum(1 for t in self.tiers if t.status == "superseded")

    @property
    def summary_line(self) -> str:
        if self.baseline_mode == "provisional":
            status = "⚠️ UNVERIFIED BASELINE" if self.overall_passed else "❌ FAIL"
        else:
            status = "✅ PASS" if self.overall_passed else "❌ FAIL"
        
        summary = (
            f"{status} [{self.method}]  "
            f"{self.tiers_passed}/{self.tiers_total} tiers passed"
        )
        if self.tiers_superseded > 0:
            summary += f" ({self.tiers_superseded} superseded)"
        summary += f"  (baseline: {self.baseline_mode})"
        return summary

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "baseline_mode": self.baseline_mode,
            "overall_passed": self.overall_passed,
            "tiers_passed": self.tiers_passed,
            "tiers_total": self.tiers_total,
            "summary": self.summary_line,
            "tiers": [t.as_dict() for t in self.tiers],
        }

    def render_console(self) -> str:
        """Return a formatted multi-line string for terminal output."""
        lines = [
            "",
            "=" * 60,
            f"  PARITY REPORT — {self.method}",
            "=" * 60,
            f"  Oracle:  {self.baseline_mode}",
            f"  Result:  {self.summary_line}",
            "-" * 60,
        ]
        for tier in self.tiers:
            status = getattr(tier, "status", None)
            if status == "superseded":
                lines.append(f"  ➖  {tier.tier} (superseded)")
                if tier.feedback:
                    for line in tier.feedback.splitlines():
                        lines.append(f"      {line}")
            elif status == "not_applicable":
                lines.append(f"  ➖  {tier.tier} (not_applicable)")
                if tier.feedback:
                    for line in tier.feedback.splitlines():
                        lines.append(f"      {line}")
            else:
                icon = "✅" if tier.passed else "❌"
                lines.append(f"  {icon}  {tier.tier}")
                if not tier.passed and tier.feedback:
                    for line in tier.feedback.splitlines():
                        lines.append(f"      {line}")
        lines.append("=" * 60)
        return "\n".join(lines)


def build_parity_report(
    method: str,
    baseline_mode: str,
    tier_results: list[TierResult],
) -> ParityReport:
    """Aggregate tier results into a ParityReport."""
    overall = all(t.passed for t in tier_results)
    return ParityReport(
        method=method,
        baseline_mode=baseline_mode,
        overall_passed=overall,
        tiers=tier_results,
    )
