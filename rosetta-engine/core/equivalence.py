import re
import types
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


MONEY_QUANTUM = Decimal("0.01")
_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_NUMERIC_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


@dataclass(frozen=True)
class EquivalenceResult:
    passed: bool
    expected_normalized: Any
    actual_normalized: Any
    differences: list[str]

    @property
    def feedback(self) -> str:
        if self.passed:
            return "Success"
        return "Equivalence mismatch:\n" + "\n".join(self.differences)


def canonical_key(key: str) -> str:
    """Convert common Java/Python field naming to snake_case."""
    separated = _CAMEL_BOUNDARY.sub(r"\1_\2", key.replace("-", "_"))
    return separated.replace(" ", "_").lower()


def _normalize_number(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
    elif isinstance(value, str) and _NUMERIC_PATTERN.fullmatch(value.strip()):
        try:
            number = Decimal(value.strip())
        except InvalidOperation:
            return value
    else:
        return value

    return number.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def normalize_json(value: Any) -> Any:
    """Normalize JSON-like data without treating missing fields as defaults."""
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            normalized[canonical_key(str(key))] = normalize_json(item)
        return normalized
    if isinstance(value, list):
        return [normalize_json(item) for item in value]
    return _normalize_number(value)


def _collect_differences(expected: Any, actual: Any, path: str = "$") -> list[str]:
    differences = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            differences.append(f"{path}.{key}: missing; expected {expected[key]!r}")
        for key in sorted(actual_keys - expected_keys):
            differences.append(f"{path}.{key}: unexpected value {actual[key]!r}")
        for key in sorted(expected_keys & actual_keys):
            differences.extend(_collect_differences(expected[key], actual[key], f"{path}.{key}"))
        return differences

    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            differences.append(f"{path}: expected {len(expected)} items, got {len(actual)}")
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            differences.extend(_collect_differences(expected_item, actual_item, f"{path}[{index}]"))
        return differences

    if expected != actual:
        differences.append(f"{path}: expected {expected!r}, got {actual!r}")
    return differences


def compare_outputs(expected: Any, actual: Any) -> EquivalenceResult:
    expected_normalized = normalize_json(expected)
    actual_normalized = normalize_json(actual)
    differences = _collect_differences(expected_normalized, actual_normalized)
    return EquivalenceResult(
        passed=not differences,
        expected_normalized=expected_normalized,
        actual_normalized=actual_normalized,
        differences=differences,
    )


def load_module_from_source(source: str, module_name: str) -> types.ModuleType:
    """Compile candidate Python source into an isolated in-memory module."""
    module = types.ModuleType(module_name)
    module.__file__ = f"<{module_name}>"
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module