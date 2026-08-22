"""
golden.py — Golden-file baseline provider for Rosetta equivalence testing.

Golden files are hand-authored JSON fixtures that mirror the arithmetic of the
legacy Java source. They are the authoritative oracle for T2 (unit arithmetic)
and T3 (golden-file equivalence) tiers. No JDK or OFBiz runtime is required at
test time; fixtures are committed to the repository and version-controlled.

Directory layout:
    rosetta-engine/tests/baselines/<method_name>/_manifest.json
    rosetta-engine/tests/baselines/<method_name>/<case_id>.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Canonical location of all golden baseline fixtures.
_BASELINES_ROOT = Path(__file__).parents[1] / "tests" / "baselines"


@dataclass(frozen=True)
class GoldenFixture:
    """A single golden-file test case."""

    fixture_id: str
    description: str
    method: str
    capture_mode: str
    arithmetic_trace: dict[str, str]
    input: dict[str, Any]
    expected_output: dict[str, Any]


@dataclass(frozen=True)
class GoldenManifest:
    """Manifest metadata for a method's set of golden fixtures."""

    method: str
    source_class: str
    formula: str
    capture_mode: str
    capture_date: str
    formula_terms: list[dict[str, Any]]
    case_ids: list[str]


class GoldenFileNotFoundError(FileNotFoundError):
    """Raised when a golden fixture file or manifest is missing."""


class GoldenFileProvider:
    """
    Loads and serves golden-file fixtures for a given legacy method.

    Usage::

        provider = GoldenFileProvider("getGrandTotal")
        fixtures = provider.all_fixtures()
        fixture  = provider.fixture("case_04_fixed_adjustment")
    """

    def __init__(self, method: str, baselines_root: Path | None = None) -> None:
        self._method = method
        self._root = (baselines_root or _BASELINES_ROOT) / method
        self._manifest: GoldenManifest | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def manifest(self) -> GoldenManifest:
        """Return the manifest for this method, loading it on first access."""
        if self._manifest is None:
            self._manifest = self._load_manifest()
        return self._manifest

    def fixture(self, case_id: str) -> GoldenFixture:
        """Load a single fixture by its case ID."""
        path = self._root / f"{case_id}.json"
        if not path.exists():
            raise GoldenFileNotFoundError(
                f"Golden fixture not found: {path}. "
                f"Available cases: {self.manifest().case_ids}"
            )
        raw = json.loads(path.read_text(encoding="utf-8"))
        return GoldenFixture(
            fixture_id=raw["fixture_id"],
            description=raw.get("description", ""),
            method=self._method,
            capture_mode=self.manifest().capture_mode,
            arithmetic_trace=raw.get("arithmetic_trace", {}),
            input=raw["input"],
            expected_output=raw["expected_output"],
        )

    def all_fixtures(self) -> list[GoldenFixture]:
        """Load every fixture listed in the manifest, in order."""
        return [self.fixture(case_id) for case_id in self.manifest().case_ids]

    def formula_terms(self) -> list[dict[str, Any]]:
        """Return the formula term list from the manifest."""
        return self.manifest().formula_terms

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_manifest(self) -> GoldenManifest:
        manifest_path = self._root / "_manifest.json"
        if not manifest_path.exists():
            raise GoldenFileNotFoundError(
                f"Golden manifest not found: {manifest_path}. "
                f"Create tests/baselines/{self._method}/_manifest.json first."
            )
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        return GoldenManifest(
            method=raw.get("method", self._method),
            source_class=raw.get("source_class", ""),
            formula=raw.get("formula", ""),
            capture_mode=raw.get("capture_mode", "unknown"),
            capture_date=raw.get("capture_date", ""),
            formula_terms=raw.get("formula_terms", []),
            case_ids=raw.get("cases", []),
        )


def list_available_methods(baselines_root: Path | None = None) -> list[str]:
    """Return method names for which golden fixtures exist."""
    root = baselines_root or _BASELINES_ROOT
    if not root.exists():
        return []
    return [
        d.name
        for d in root.iterdir()
        if d.is_dir() and (d / "_manifest.json").exists()
    ]
