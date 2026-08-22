from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List


def calculate_getGrandTotal(request: Dict[str, Any]) -> Dict[str, str]:
    """
    Compute the grand total of an order based on the supplied request payload.

    Expected output keys (all always present):
        - sub_total
        - total_shipping
        - total_sales_tax
        - order_other_adjustment_total
        - order_global_adjustments
        - grand_total

    All monetary values are returned as strings formatted to two decimal places.
    """

    def to_decimal(value: Any) -> Decimal:
        """Convert a value that may be int, float, str or Decimal to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    # ------------------------------------------------------------------
    # 1. Sub‑total from order lines
    # ------------------------------------------------------------------
    order_lines: List[Dict[str, Any]] = request.get("orderLines", [])
    sub_total = sum(
        (
            to_decimal(line.get("quantity", 0))
            * to_decimal(line.get("unitPrice", 0))
        )
        for line in order_lines
    , Decimal('0'))

    # ------------------------------------------------------------------
    # 2. Shipping and tax from ship groups
    # ------------------------------------------------------------------
    ship_groups: List[Dict[str, Any]] = request.get("shipGroups", [])
    total_shipping = sum(
        to_decimal(group.get("shippingCost", 0)) for group in ship_groups
    , Decimal('0'))

    total_sales_tax = sum(
        to_decimal(group.get("salesTax", 0)) for group in ship_groups
    , Decimal('0'))

    # ------------------------------------------------------------------
    # 3. Other (non‑global) adjustments
    # ------------------------------------------------------------------
    other_adjustments: List[Dict[str, Any]] = request.get("adjustments", {}).get("other", [])
    order_other_adjustment_total = Decimal('0')
    for adj in other_adjustments:
        amount = to_decimal(adj.get("amount", 0))
        if adj.get("is_percent", False):
            # Percentage of sub_total
            amount = (sub_total * amount) / Decimal('100')
        order_other_adjustment_total += amount

    # ------------------------------------------------------------------
    # 4. Global adjustments (respect ship_group_seq_id filter)
    # ------------------------------------------------------------------
    global_adjustments: List[Dict[str, Any]] = request.get("adjustments", {}).get("global", [])
    order_global_adjustments = Decimal('0')
    for adj in global_adjustments:
        ship_group_seq_id = adj.get("ship_group_seq_id")
        # Include only if ship_group_seq_id is None or exactly "_NA_"
        if ship_group_seq_id is not None and ship_group_seq_id != "_NA_":
            continue
        amount = to_decimal(adj.get("amount", 0))
        if adj.get("is_percent", False):
            amount = (sub_total * amount) / Decimal('100')
        order_global_adjustments += amount

    # ------------------------------------------------------------------
    # 5. Grand total
    # ------------------------------------------------------------------
    grand_total = (
        sub_total
        + total_shipping
        + total_sales_tax
        + order_other_adjustment_total
        + order_global_adjustments
    )

    # Helper to format Decimal to string with two decimal places
    def fmt(value: Decimal) -> str:
        return str(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    return {
        "sub_total": fmt(sub_total),
        "total_shipping": fmt(total_shipping),
        "total_sales_tax": fmt(total_sales_tax),
        "order_other_adjustment_total": fmt(order_other_adjustment_total),
        "order_global_adjustments": fmt(order_global_adjustments),
        "grand_total": fmt(grand_total),
    }