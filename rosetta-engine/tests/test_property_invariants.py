"""
test_property_invariants.py — T4: Property-based invariant testing.

Uses the `hypothesis` library to generate hundreds of random inputs and verify
that the getGrandTotal service satisfies its mathematical invariants for ALL
valid inputs, not just the curated golden fixtures.

Invariants tested:
  1. grand_total == sub_total + total_shipping + total_sales_tax
               + order_other_adjustment_total + order_global_adjustments
  2. sub_total == sum(cart_lines[i].item_sub_total)
  3. total_shipping == sum(ship_info[i].ship_estimate)
  4. total_sales_tax == sum(ship_info[i].total_tax)
  5. Grand total is deterministic: same inputs → same output
  6. Global adjustments with a real ship_group_seq_id are excluded
  7. Global adjustments with ship_group_seq_id in (null, '_NA_') are included

These tests require no JDK, no OFBiz, no LLM, and no network access.
Install hypothesis: pip install hypothesis
"""

import sys
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

try:
    from hypothesis import given, settings, HealthCheck, assume
    from hypothesis import strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.equivalence import load_module_from_source

_SERVICE_PATH = Path(__file__).parents[2] / "modern-invoices" / "getGrandTotal_service.py"
_MONEY_QUANTUM = Decimal("0.01")


def _make_client() -> TestClient:
    source = _SERVICE_PATH.read_text(encoding="utf-8")
    module = load_module_from_source(source, "getGrandTotal_property_test")
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def _q(value: str | float | Decimal) -> Decimal:
    """Quantize to cents precision."""
    return Decimal(str(value)).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

if HYPOTHESIS_AVAILABLE:
    # Money amounts as strings, bounded to a realistic range
    _money = st.decimals(
        min_value=Decimal("0.00"),
        max_value=Decimal("9999.99"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ).map(lambda d: str(d.quantize(_MONEY_QUANTUM)))

    _signed_money = st.decimals(
        min_value=Decimal("-999.99"),
        max_value=Decimal("999.99"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ).map(lambda d: str(d.quantize(_MONEY_QUANTUM)))

    _cart_line = st.fixed_dictionaries({"item_sub_total": _money})

    _ship_info = st.fixed_dictionaries({
        "ship_estimate": _money,
        "total_tax": _money,
    })

    _adjustment = st.fixed_dictionaries({
        "amount": _signed_money,
        "is_percent": st.just(False),          # non-percent: simpler to verify
        "ship_group_seq_id": st.none(),
    })

    _global_adjustment_included = st.fixed_dictionaries({
        "amount": _signed_money,
        "is_percent": st.just(False),
        "ship_group_seq_id": st.one_of(st.none(), st.just("_NA_")),
    })

    _global_adjustment_excluded = st.fixed_dictionaries({
        "amount": _signed_money,
        "is_percent": st.just(False),
        "ship_group_seq_id": st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            min_size=3,
            max_size=8,
        ).filter(lambda s: s != "_NA_"),
    })

    _request = st.fixed_dictionaries({
        "cart_lines": st.lists(_cart_line, min_size=0, max_size=10),
        "ship_info": st.lists(_ship_info, min_size=0, max_size=5),
        "adjustments": st.lists(_adjustment, min_size=0, max_size=5),
        "global_adjustments": st.lists(
            st.one_of(_global_adjustment_included, _global_adjustment_excluded),
            min_size=0,
            max_size=5,
        ),
    })


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(HYPOTHESIS_AVAILABLE, "hypothesis not installed — run: pip install hypothesis")
class T4PropertyInvariantTests(unittest.TestCase):

    @given(_request)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_invariant_grand_total_equals_sum_of_parts(self, payload):
        """
        INVARIANT 1: grand_total == sub_total + total_shipping + total_sales_tax
                                  + order_other_adjustment_total + order_global_adjustments
        """
        client = _make_client()
        response = client.post("/calculate-grand-total", json=payload)
        self.assertEqual(response.status_code, 200, response.text)

        data = response.json()
        sub_total = _q(data["sub_total"])
        total_shipping = _q(data["total_shipping"])
        total_sales_tax = _q(data["total_sales_tax"])
        other_adj = _q(data["order_other_adjustment_total"])
        global_adj = _q(data["order_global_adjustments"])
        grand_total = _q(data["grand_total"])

        expected_grand_total = (sub_total + total_shipping + total_sales_tax
                                + other_adj + global_adj)
        self.assertEqual(
            grand_total, expected_grand_total,
            msg=(
                f"grand_total invariant violated:\n"
                f"  sub_total={sub_total}, total_shipping={total_shipping}, "
                f"total_sales_tax={total_sales_tax},\n"
                f"  order_other_adjustment_total={other_adj}, "
                f"order_global_adjustments={global_adj}\n"
                f"  Expected grand_total={expected_grand_total}, Got={grand_total}\n"
                f"  Payload: {payload}"
            ),
        )

    @given(st.lists(_cart_line, min_size=0, max_size=15))
    @settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
    def test_invariant_sub_total_equals_sum_of_line_items(self, cart_lines):
        """
        INVARIANT 2: sub_total == sum(cart_lines[i].item_sub_total)
        """
        payload = {
            "cart_lines": cart_lines,
            "ship_info": [],
            "adjustments": [],
            "global_adjustments": [],
        }
        client = _make_client()
        response = client.post("/calculate-grand-total", json=payload)
        self.assertEqual(response.status_code, 200, response.text)

        expected_sub_total = sum(
            _q(line["item_sub_total"]) for line in cart_lines
        )
        actual_sub_total = _q(response.json()["sub_total"])
        self.assertEqual(
            actual_sub_total, expected_sub_total,
            msg=(
                f"sub_total invariant violated:\n"
                f"  Expected {expected_sub_total}, Got {actual_sub_total}\n"
                f"  cart_lines: {cart_lines}"
            ),
        )

    @given(st.lists(_ship_info, min_size=0, max_size=5))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_invariant_shipping_and_tax_equal_sum_of_ship_groups(self, ship_info):
        """
        INVARIANT 3 + 4: total_shipping and total_sales_tax are sums of ship group fields.
        """
        payload = {
            "cart_lines": [],
            "ship_info": ship_info,
            "adjustments": [],
            "global_adjustments": [],
        }
        client = _make_client()
        response = client.post("/calculate-grand-total", json=payload)
        self.assertEqual(response.status_code, 200, response.text)

        data = response.json()
        expected_shipping = sum(_q(s["ship_estimate"]) for s in ship_info)
        expected_tax = sum(_q(s["total_tax"]) for s in ship_info)

        self.assertEqual(_q(data["total_shipping"]), expected_shipping,
                         f"total_shipping invariant violated. ship_info={ship_info}")
        self.assertEqual(_q(data["total_sales_tax"]), expected_tax,
                         f"total_sales_tax invariant violated. ship_info={ship_info}")

    @given(_request)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_invariant_determinism(self, payload):
        """
        INVARIANT 5: Same input always produces same output (no hidden state).
        """
        client = _make_client()
        r1 = client.post("/calculate-grand-total", json=payload).json()
        r2 = client.post("/calculate-grand-total", json=payload).json()
        self.assertEqual(r1, r2, f"Non-deterministic result for payload: {payload}")

    @given(st.lists(_global_adjustment_excluded, min_size=1, max_size=5))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_invariant_ship_group_adjustments_are_excluded(self, excluded_adjs):
        """
        INVARIANT 6: Global adjustments with a real ship_group_seq_id contribute 0 to
        order_global_adjustments.
        """
        payload = {
            "cart_lines": [],
            "ship_info": [],
            "adjustments": [],
            "global_adjustments": excluded_adjs,
        }
        client = _make_client()
        response = client.post("/calculate-grand-total", json=payload)
        self.assertEqual(response.status_code, 200, response.text)

        actual_global = _q(response.json()["order_global_adjustments"])
        self.assertEqual(
            actual_global, Decimal("0.00"),
            msg=(
                f"Ship-group adjustment exclusion invariant violated: "
                f"expected 0.00, got {actual_global}. adjustments={excluded_adjs}"
            ),
        )

    @given(st.lists(_global_adjustment_included, min_size=1, max_size=5))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_invariant_null_na_adjustments_are_included(self, included_adjs):
        """
        INVARIANT 7: Global adjustments with ship_group_seq_id in (null, '_NA_')
        are included in order_global_adjustments.
        """
        payload = {
            "cart_lines": [],
            "ship_info": [],
            "adjustments": [],
            "global_adjustments": included_adjs,
        }
        client = _make_client()
        response = client.post("/calculate-grand-total", json=payload)
        self.assertEqual(response.status_code, 200, response.text)

        actual_global = _q(response.json()["order_global_adjustments"])
        expected = sum(_q(a["amount"]) for a in included_adjs)
        self.assertEqual(
            actual_global, expected,
            msg=(
                f"Null/_NA_ inclusion invariant violated: "
                f"expected {expected}, got {actual_global}. adjustments={included_adjs}"
            ),
        )


# ---------------------------------------------------------------------------
# Graceful degradation when hypothesis is not installed
# ---------------------------------------------------------------------------

class T4AvailabilityCheck(unittest.TestCase):
    def test_hypothesis_import_check(self):
        """Informational: reports whether hypothesis is installed."""
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest(
                "hypothesis is not installed. Run: pip install hypothesis\n"
                "T4 property tests will be skipped until it is available."
            )
        self.assertTrue(True, "hypothesis is available")


if __name__ == "__main__":
    unittest.main()
