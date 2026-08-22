"""
formula_ir.py — Formula Intermediate Representation and T1 completeness checking.

T1 (Formula Completeness) is the first and cheapest validation tier. It runs
before any candidate Python code is executed. It checks that the generated
response JSON contains every field declared as `required` in the formula IR,
and that no required field is entirely absent from the response.

This tier catches the most common LLM generation failure: silently dropping one
of the formula terms (e.g. returning `grand_total` without `total_shipping`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FormulaTerm:
    name: str                  # canonical snake_case field name
    source_method: str         # corresponding Java method
    required: bool = True


@dataclass(frozen=True)
class FormulaIR:
    """
    Intermediate Representation of a legacy method's business formula.

    Extracted either from Discovery Agent output or from a golden manifest.
    """
    method_name: str
    formula: str                          # human-readable expression
    terms: list[FormulaTerm] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def required_term_names(self) -> list[str]:
        return [t.name for t in self.terms if t.required]


# ---------------------------------------------------------------------------
# T1 result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class T1Result:
    passed: bool
    missing_terms: list[str]
    extra_terms: list[str]
    checked_terms: list[str]

    @property
    def feedback(self) -> str:
        if self.passed:
            return "T1 Formula Completeness: PASS"
        parts = []
        if self.missing_terms:
            parts.append(
                "Missing required fields in response: "
                + ", ".join(self.missing_terms)
            )
        return "T1 Formula Completeness FAIL — " + "; ".join(parts)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": "T1_formula_completeness",
            "passed": self.passed,
            "missing_terms": self.missing_terms,
            "extra_terms": self.extra_terms,
            "checked_terms": self.checked_terms,
        }


# ---------------------------------------------------------------------------
# Extraction from Discovery JSON output
# ---------------------------------------------------------------------------

_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def _to_snake(name: str) -> str:
    separated = _CAMEL_BOUNDARY.sub(r"\1_\2", name.replace("-", "_"))
    return separated.replace(" ", "_").lower()


def extract_formula_ir_from_logic_json(logic_json_str: str) -> FormulaIR | None:
    """
    Parse FormulaIR from the JSON string returned by the Discovery Agent.

    Returns None if the JSON does not contain enough formula data; the caller
    should fall back to the golden manifest if available.

    Expected structure (subset):
    {
      "method_name": "getGrandTotal",
      "formula_terms": [
        {"name": "sub_total", "source_method": "getSubTotal", "required": true},
        ...
      ],
      "mathematical_formula": "sub_total + total_shipping + ..."
    }
    """
    try:
        data = json.loads(logic_json_str)
    except (json.JSONDecodeError, TypeError):
        return None

    raw_terms = data.get("formula_terms") or data.get("components")
    if not raw_terms:
        return None

    terms: list[FormulaTerm] = []
    if isinstance(raw_terms, list):
        for t in raw_terms:
            if isinstance(t, dict) and "name" in t:
                terms.append(FormulaTerm(
                    name=_to_snake(t["name"]),
                    source_method=t.get("source_method", ""),
                    required=bool(t.get("required", True)),
                ))
    elif isinstance(raw_terms, dict):
        # Older format: components dict keyed by field name
        for name in raw_terms:
            terms.append(FormulaTerm(
                name=_to_snake(name),
                source_method="",
                required=True,
            ))

    if not terms:
        return None

    return FormulaIR(
        method_name=data.get("method_name", "unknown"),
        formula=data.get("mathematical_formula", data.get("formula", "")),
        terms=terms,
        raw=data,
    )


def formula_ir_from_manifest_terms(
    method_name: str,
    manifest_terms: list[dict[str, Any]],
    formula: str = "",
) -> FormulaIR:
    """Build a FormulaIR from golden manifest term list (fallback when Discovery IR missing)."""
    terms = [
        FormulaTerm(
            name=_to_snake(t["name"]),
            source_method=t.get("source_method", ""),
            required=bool(t.get("required", True)),
        )
        for t in manifest_terms
    ]
    return FormulaIR(method_name=method_name, formula=formula, terms=terms)


# ---------------------------------------------------------------------------
# T1 check
# ---------------------------------------------------------------------------

def check_formula_completeness(
    formula_ir: FormulaIR,
    response_json: dict[str, Any],
) -> T1Result:
    """
    T1: Verify that every required formula term is present in the response.

    Key naming in the response is normalised to snake_case before comparison,
    so `subTotal` and `sub_total` are treated as equivalent.
    """
    response_keys = {_to_snake(k) for k in response_json}
    required = formula_ir.required_term_names

    missing = [name for name in required if name not in response_keys]
    # Extra terms: present in response but not in the IR (informational only)
    extra = [k for k in response_keys if k not in required]

    return T1Result(
        passed=not missing,
        missing_terms=missing,
        extra_terms=extra,
        checked_terms=required,
    )
