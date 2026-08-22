import unittest
from pathlib import Path

from core.equivalence import compare_outputs
from core.baseline import BaselineError, execute_legacy_baseline
from core.validator import validator_node


class EquivalenceTests(unittest.TestCase):
    def test_normalizes_field_names_and_decimal_transport_values(self):
        result = compare_outputs(
            {"subTotal": 120.0, "grand_total": 130.4},
            {"sub_total": "120.00", "grand_total": "130.40"},
        )

        self.assertTrue(result.passed, result.feedback)

    def test_preserves_real_monetary_mismatch(self):
        result = compare_outputs(
            {"grand_total": 130.4},
            {"grand_total": "129.40"},
        )

        self.assertFalse(result.passed)
        self.assertIn("$.grand_total", result.feedback)

    def test_reports_missing_fields(self):
        result = compare_outputs(
            {"subTotal": 120.0, "grandTotal": 130.4},
            {"sub_total": "120.00"},
        )

        self.assertFalse(result.passed)
        self.assertIn("$.grand_total: missing", result.feedback)

    def test_validator_executes_candidate_source_from_state(self):
        """Shadow tier: candidate with 2 of 5 terms passes when no formula IR or golden fixtures exist.
        Uses 'stubMethod' which has no golden baselines, so T1 and T3 are both skipped."""
        candidate_source = """
def calculate_stubMethod(request: dict):
    return {'sub_total': '120.00', 'grand_total': '130.40'}
"""
        result = validator_node({
            "target_method": "stubMethod",   # no golden fixtures → T1 + T3 both skipped
            "java_code": "",
            "generated_python": candidate_source,
            "candidate_source": candidate_source,
            "candidate_route": "/calculate-grand-total",
            "candidate_method": "POST",
            "test_payload": {"items": []},
            "expected_legacy_output": {"subTotal": 120.0, "grand_total": 130.4},
            "formula_ir": None,
            "logic_json": None,
            "retry_count": 0,
        })

        self.assertTrue(result["validation_passed"], result.get("validation_feedback"))

    def test_validator_rejects_real_candidate_mismatch(self):
        """Shadow tier: real numeric mismatch is rejected even without T1."""
        candidate_source = """
def calculate_getGrandTotal(request: dict):
    return {'grand_total': '129.40'}
"""
        result = validator_node({
            "target_method": "getGrandTotal",
            "java_code": "",
            "generated_python": candidate_source,
            "candidate_source": candidate_source,
            "candidate_route": "/calculate-grand-total",
            "candidate_method": "POST",
            "test_payload": {"items": []},
            "expected_legacy_output": {"grand_total": 130.4},
            # Clear formula_ir so this test isolates shadow-tier mismatch, not T1.
            "formula_ir": None,
            "logic_json": None,
            "retry_count": 0,
        })

        self.assertFalse(result["validation_passed"])
        self.assertIn("$.grand_total", result["validation_feedback"])

    def test_validator_rejects_ambiguous_router_without_contract(self):
        # With the pure function refactor, the routing ambiguity problem is obsolete.
        # This test ensures we gracefully handle a missing candidate function instead.
        candidate_source = """
def calculate_wrongName(request: dict):
    return {'grand_total': '130.40'}
"""
        result = validator_node({
            "target_method": "getGrandTotal",
            "java_code": "",
            "candidate_source": candidate_source,
            "test_payload": {},
            "expected_legacy_output": {"grand_total": 130.4},
            "retry_count": 0,
        })

        self.assertFalse(result["validation_passed"])
        self.assertIn("missing required function", result["validation_feedback"])

    def test_checked_in_grand_total_service_passes_canonical_case(self):
        # Read the generated function instead of the wrapped service
        service_path = Path(__file__).parents[2] / "modern-invoices" / "getGrandTotal_function.py"
        candidate_source = service_path.read_text(encoding="utf-8")
        result = validator_node({
            "target_method": "getGrandTotal",
            "java_code": "",
            "candidate_source": candidate_source,
            "test_cases": [{
                "name": "all_components",
                "payload": {
                    "cart_lines": [{"item_sub_total": "120.00"}],
                    "ship_info": [{"ship_estimate": "10.00", "total_tax": "8.40"}],
                    "adjustments": [{"amount": "-10.00"}],
                    "global_adjustments": [{"amount": "2.00", "ship_group_seq_id": None}],
                },
                "expected_output": {
                    "subTotal": 120.0,
                    "totalShipping": 10.0,
                    "totalSalesTax": 8.4,
                    "orderOtherAdjustmentTotal": -10.0,
                    "orderGlobalAdjustments": 2.0,
                    "grand_total": 130.4,
                },
            }],
            "baseline_mode": "approved",
            "retry_count": 0,
        })

        self.assertTrue(result["validation_passed"], result.get("validation_feedback"))

    def test_validator_runs_all_cases_and_stops_on_failure(self):
        """Shadow tier: validator stops on first failing case and reports it.
        Uses a fictional method name with no golden fixtures so only the shadow tier runs."""
        candidate_source = """
def calculate_stubMethod(request: dict):
    return {'grand_total': '130.40'}
"""
        result = validator_node({
            "target_method": "stubMethod",   # no golden fixtures → T1 + T3 skipped
            "java_code": "",
            "generated_python": candidate_source,
            "candidate_source": candidate_source,
            "formula_ir": None,
            "logic_json": None,
            "test_cases": [
                {"name": "passing", "payload": {}, "expected_output": {"grand_total": 130.4}},
                {"name": "failing", "payload": {}, "expected_output": {"grand_total": 131.4}},
            ],
            "baseline_mode": "approved",
            "retry_count": 0,
        })

        self.assertFalse(result["validation_passed"])
        self.assertEqual(
            [case["name"] for case in result["validation_results"]],
            ["passing", "failing"],
        )
        self.assertIn("Case 'failing'", result["validation_feedback"])

    def test_java_executed_mode_requires_an_adapter_command(self):
        with self.assertRaises(BaselineError):
            execute_legacy_baseline(None, {})

    def test_java_executed_mode_fails_closed_when_adapter_output_is_invalid(self):
        with self.assertRaises(BaselineError):
            execute_legacy_baseline("python -c pass", {})


if __name__ == "__main__":
    unittest.main()