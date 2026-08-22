"""
parity_endpoint.py — FastAPI router exposing the parity report API.

Endpoints:
  GET  /parity/methods              — list methods with golden fixtures
  GET  /parity/{method}             — run T1-T3 tiers and return full report
  GET  /parity/{method}/fixtures    — list golden fixtures for a method
  GET  /parity/{method}/{case_id}   — return a single golden fixture

This router is auto-discovered by modern-invoices/main.py and mounted at runtime.
The parity report is computed on demand so it always reflects the current state
of the checked-in service artifact.
"""

import sys
from pathlib import Path

# Make rosetta-engine importable
_ENGINE_PATH = Path(__file__).parents[1] / "rosetta-engine"
if str(_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(_ENGINE_PATH))

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.golden import GoldenFileProvider, GoldenFileNotFoundError, list_available_methods
from core.equivalence import compare_outputs, load_module_from_source
from core.formula_ir import formula_ir_from_manifest_terms, check_formula_completeness
from core.parity_report import TierResult, build_parity_report

router = APIRouter(tags=["Parity"])

_SERVICES_DIR = Path(__file__).parent


def _load_service_client(method: str) -> TestClient:
    """Load the generated service for a given method name."""
    service_file = _SERVICES_DIR / f"{method}_service.py"
    if not service_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No generated service found for method '{method}'. "
                   f"Expected: {service_file.name}",
        )
    source = service_file.read_text(encoding="utf-8")
    module = load_module_from_source(source, f"{method}_parity")
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def _run_parity(method: str) -> dict[str, Any]:
    """Execute T1 + T3 parity tiers and return a ParityReport dict."""
    try:
        provider = GoldenFileProvider(method)
        manifest = provider.manifest()
    except GoldenFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    try:
        client = _load_service_client(method)
    except HTTPException:
        raise

    formula_ir = formula_ir_from_manifest_terms(
        method_name=method,
        manifest_terms=manifest.formula_terms,
        formula=manifest.formula,
    )

    tier_results: list[TierResult] = []

    # ---- T1: Formula Completeness ----------------------------------------
    probe = client.post(f"/calculate-{_method_to_path(method)}", json={})
    if probe.status_code == 200:
        t1 = check_formula_completeness(formula_ir, probe.json())
        tier_results.append(TierResult(
            tier="T1_formula_completeness",
            passed=t1.passed,
            feedback=t1.feedback,
            details=t1.as_dict(),
        ))
    else:
        tier_results.append(TierResult(
            tier="T1_formula_completeness",
            passed=False,
            feedback=f"T1 probe returned HTTP {probe.status_code}",
        ))

    # ---- T3: Golden-File Equivalence -------------------------------------
    golden_cases: list[dict] = []
    golden_passed = True
    for fixture in provider.all_fixtures():
        response = client.post(
            f"/calculate-{_method_to_path(method)}", json=fixture.input
        )
        if response.status_code != 200:
            golden_cases.append({
                "fixture_id": fixture.fixture_id,
                "description": fixture.description,
                "passed": False,
                "feedback": f"HTTP {response.status_code}",
            })
            golden_passed = False
            continue
        comparison = compare_outputs(fixture.expected_output, response.json())
        golden_cases.append({
            "fixture_id": fixture.fixture_id,
            "description": fixture.description,
            "passed": comparison.passed,
            "differences": comparison.differences,
            "expected_normalized": _decimal_safe(comparison.expected_normalized),
            "actual_normalized": _decimal_safe(comparison.actual_normalized),
            "arithmetic_trace": fixture.arithmetic_trace,
        })
        if not comparison.passed:
            golden_passed = False

    tier_results.append(TierResult(
        tier="T3_golden_file_equivalence",
        passed=golden_passed,
        feedback="T3 Golden-File: PASS" if golden_passed else "T3 Golden-File: FAIL",
        details={"cases": golden_cases, "capture_mode": manifest.capture_mode},
    ))

    report = build_parity_report(method, "golden_file", tier_results)
    return report.as_dict()


def _method_to_path(method: str) -> str:
    """Convert camelCase method name to kebab-case endpoint path segment."""
    import re
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", method)
    return s.lower()


def _decimal_safe(obj: Any) -> Any:
    """Recursively convert Decimal to str for JSON serialization."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _decimal_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_safe(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/parity/methods", summary="List methods with golden fixtures")
async def list_parity_methods() -> dict[str, Any]:
    """Return all method names for which golden baseline fixtures exist."""
    methods = list_available_methods()
    return {
        "methods": methods,
        "count": len(methods),
    }


@router.get("/parity/{method}", summary="Run T1 + T3 parity tiers for a method")
async def get_parity_report(method: str) -> dict[str, Any]:
    """
    Execute T1 (formula completeness) and T3 (golden-file equivalence) against
    the checked-in generated service and return the aggregated parity report.

    T4 (property-based invariants) are run via `pytest` and are not included in
    the live endpoint (they require hypothesis and are too slow for an HTTP call).
    """
    report = _run_parity(method)
    return _decimal_safe(report)


@router.get("/parity/{method}/fixtures", summary="List golden fixtures for a method")
async def list_fixtures(method: str) -> dict[str, Any]:
    """Return fixture IDs and descriptions from the golden manifest."""
    try:
        provider = GoldenFileProvider(method)
        manifest = provider.manifest()
        fixtures = [
            {
                "fixture_id": f.fixture_id,
                "description": f.description,
                "capture_mode": f.capture_mode,
            }
            for f in provider.all_fixtures()
        ]
    except GoldenFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "method": method,
        "formula": manifest.formula,
        "capture_mode": manifest.capture_mode,
        "capture_date": manifest.capture_date,
        "fixtures": fixtures,
    }


@router.get("/parity/{method}/{case_id}", summary="Return a single golden fixture")
async def get_fixture(method: str, case_id: str) -> dict[str, Any]:
    """Return the full golden fixture including input, expected output, and arithmetic trace."""
    try:
        provider = GoldenFileProvider(method)
        fixture = provider.fixture(case_id)
    except GoldenFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "fixture_id": fixture.fixture_id,
        "description": fixture.description,
        "capture_mode": fixture.capture_mode,
        "arithmetic_trace": fixture.arithmetic_trace,
        "input": fixture.input,
        "expected_output": fixture.expected_output,
    }
