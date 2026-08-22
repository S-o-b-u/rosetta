"""
test_golden_equivalence.py — T2 (unit arithmetic) and T3 (golden-file) tests.

T2: Validates that the checked-in getGrandTotal_service.py produces the correct
    arithmetic for every golden fixture case. These tests are deterministic and
    require no LLM calls, no JDK, and no OFBiz runtime.

T3: Validates that compare_outputs() accepts the service response as equivalent
    to the golden expected_output, covering normalization of camelCase keys and
    Decimal/string representations.

Each test method maps 1-to-1 to a golden fixture case so failures point
directly to the problematic case and its arithmetic_trace.
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

# Make sure the engine package is importable when running from the tests dir
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.golden import GoldenFileProvider, GoldenFixture
from core.equivalence import compare_outputs, load_module_from_source

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SERVICE_PATH = Path(__file__).parents[2] / "modern-invoices" / "getGrandTotal_service.py"
_PROVIDER = GoldenFileProvider("getGrandTotal")


def _make_client() -> TestClient:
    source = _SERVICE_PATH.read_text(encoding="utf-8")
    module = load_module_from_source(source, "getGrandTotal_golden_test")
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def _run_fixture(fixture: GoldenFixture) -> dict:
    """POST the fixture input to the service and return the JSON response."""
    client = _make_client()
    response = client.post("/calculate-grand-total", json=fixture.input)
    assert response.status_code == 200, (
        f"[{fixture.fixture_id}] HTTP {response.status_code}: {response.text}"
    )
    return response.json()


# ---------------------------------------------------------------------------
# T2 — Unit arithmetic tests (one per golden case)
# ---------------------------------------------------------------------------

class T2UnitArithmeticTests(unittest.TestCase):
    """
    Each test verifies one complete golden fixture against the service.
    Failures include the arithmetic_trace so the developer knows the expected math.
    """

    def _assert_fixture(self, fixture: GoldenFixture) -> None:
        actual = _run_fixture(fixture)
        result = compare_outputs(fixture.expected_output, actual)
        trace_str = "\n".join(
            f"  {k}: {v}" for k, v in fixture.arithmetic_trace.items()
        )
        self.assertTrue(
            result.passed,
            msg=(
                f"\n[{fixture.fixture_id}] {fixture.description}\n"
                f"Arithmetic trace:\n{trace_str}\n"
                f"Differences:\n{result.feedback}"
            ),
        )

    def test_case_01_empty_cart(self):
        """All inputs empty — every output field must be 0.00."""
        self._assert_fixture(_PROVIDER.fixture("case_01_empty_cart"))

    def test_case_02_single_item(self):
        """Single cart line, no shipping/tax/adjustments."""
        self._assert_fixture(_PROVIDER.fixture("case_02_single_item"))

    def test_case_03_multi_item_with_tax(self):
        """Three items + shipping + tax — canonical 5-term exercise."""
        self._assert_fixture(_PROVIDER.fixture("case_03_multi_item_with_tax"))

    def test_case_04_fixed_adjustment(self):
        """Fixed negative discount + global adjustment. Grand total = 130.40."""
        self._assert_fixture(_PROVIDER.fixture("case_04_fixed_adjustment"))

    def test_case_05_percentage_adjustment(self):
        """10% percentage discount on sub_total."""
        self._assert_fixture(_PROVIDER.fixture("case_05_percentage_adjustment"))

    def test_case_06_global_adjustment_na(self):
        """Global adjustment with ship_group_seq_id='_NA_' — must be included."""
        self._assert_fixture(_PROVIDER.fixture("case_06_global_adjustment_na"))

    def test_case_07_ship_group_excluded(self):
        """Global adjustment with a real ship group ID — must be excluded."""
        self._assert_fixture(_PROVIDER.fixture("case_07_ship_group_excluded"))


# ---------------------------------------------------------------------------
# T3 — Golden-file equivalence tests (normalization layer)
# ---------------------------------------------------------------------------

class T3GoldenFileEquivalenceTests(unittest.TestCase):
    """
    Tests that compare_outputs() correctly accepts equivalent representations
    (camelCase vs snake_case, Decimal string vs float) while still rejecting
    genuine numeric differences.
    """

    def test_camel_and_snake_keys_are_equivalent(self):
        """camelCase expected keys normalize to match snake_case actual keys."""
        expected = {
            "subTotal": "120.00",
            "totalShipping": "10.00",
            "totalSalesTax": "8.40",
            "orderOtherAdjustmentTotal": "-10.00",
            "orderGlobalAdjustments": "2.00",
            "grandTotal": "130.40",
        }
        actual = {
            "sub_total": "120.00",
            "total_shipping": "10.00",
            "total_sales_tax": "8.40",
            "order_other_adjustment_total": "-10.00",
            "order_global_adjustments": "2.00",
            "grand_total": "130.40",
        }
        result = compare_outputs(expected, actual)
        self.assertTrue(result.passed, result.feedback)

    def test_float_and_decimal_string_are_equivalent(self):
        """Float 130.4 and string '130.40' normalize to the same Decimal."""
        result = compare_outputs({"grand_total": 130.4}, {"grand_total": "130.40"})
        self.assertTrue(result.passed, result.feedback)

    def test_genuine_cent_mismatch_still_fails(self):
        """130.40 vs 130.41 must fail even after normalization."""
        result = compare_outputs({"grand_total": "130.40"}, {"grand_total": "130.41"})
        self.assertFalse(result.passed)
        self.assertIn("$.grand_total", result.feedback)

    def test_missing_term_fails_after_normalization(self):
        """A response missing one formula term must fail, not silently default."""
        result = compare_outputs(
            {
                "sub_total": "120.00",
                "grand_total": "130.40",
            },
            {
                "sub_total": "120.00",
                # grand_total missing
            },
        )
        self.assertFalse(result.passed)
        self.assertIn("$.grand_total: missing", result.feedback)

    def test_all_golden_cases_pass_normalization(self):
        """Every golden fixture produces output that compare_outputs() accepts."""
        client = _make_client()
        for fixture in _PROVIDER.all_fixtures():
            with self.subTest(fixture_id=fixture.fixture_id):
                response = client.post("/calculate-grand-total", json=fixture.input)
                self.assertEqual(
                    response.status_code, 200,
                    f"[{fixture.fixture_id}] HTTP {response.status_code}: {response.text}",
                )
                result = compare_outputs(fixture.expected_output, response.json())
                self.assertTrue(
                    result.passed,
                    msg=(
                        f"[{fixture.fixture_id}] {fixture.description}\n"
                        f"{result.feedback}"
                    ),
                )


# ---------------------------------------------------------------------------
# Golden manifest and provider tests
# ---------------------------------------------------------------------------

class GoldenProviderTests(unittest.TestCase):

    def test_manifest_loads_correctly(self):
        manifest = _PROVIDER.manifest()
        self.assertEqual(manifest.method, "getGrandTotal")
        self.assertGreater(len(manifest.formula_terms), 0)
        self.assertEqual(len(manifest.case_ids), 7)

    def test_all_fixtures_load_without_error(self):
        fixtures = _PROVIDER.all_fixtures()
        self.assertEqual(len(fixtures), 7)
        for f in fixtures:
            self.assertIn("grand_total", f.expected_output)

    def test_fixture_not_found_raises_descriptive_error(self):
        from core.golden import GoldenFileNotFoundError
        with self.assertRaises(GoldenFileNotFoundError):
            _PROVIDER.fixture("nonexistent_case")


if __name__ == "__main__":
    unittest.main()
