from decimal import Decimal
from typing import Any, Dict, List


def calculate_getGrandTotal(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute the grand total of an order from the supplied request payload.

    Expected keys (both snake_case and camelCase are accepted):
        - cart_lines / cartLines
        - ship_info / shipGroups
        - adjustments / orderAdjustments
        - global_adjustments / globalAdjustments

    Returns a dict containing every component of the formula and the final
    grand_total, all as ``Decimal`` objects.
    """

    def _to_decimal(value: Any) -> Decimal:
        """Convert a value that may be str, int, float or Decimal to Decimal."""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            return Decimal(value)
        return Decimal("0")

    # ---------------------------------------------------------------------
    # Sub‑total
    # ---------------------------------------------------------------------
    cart_lines: List[Dict[str, Any]] = request.get("cart_lines") or request.get(
        "cartLines", []
    )
    sub_total = Decimal("0")
    for line in cart_lines:
        if "item_sub_total" in line:
            sub_total += _to_decimal(line["item_sub_total"])
        elif "price" in line and "quantity" in line:
            sub_total += _to_decimal(line["price"]) * _to_decimal(line["quantity"])

    # ---------------------------------------------------------------------
    # Shipping & Sales Tax
    # ---------------------------------------------------------------------
    ship_info: List[Dict[str, Any]] = request.get("ship_info") or request.get(
        "shipGroups", []
    )
    total_shipping = Decimal("0")
    total_sales_tax = Decimal("0")
    for grp in ship_info:
        total_shipping += _to_decimal(
            grp.get("ship_estimate") or grp.get("shippingCost") or 0
        )
        total_sales_tax += _to_decimal(
            grp.get("total_tax") or grp.get("salesTax") or 0
        )

    # ---------------------------------------------------------------------
    # Order‑level adjustments (not tied to a ship group)
    # ---------------------------------------------------------------------
    adjustments: List[Dict[str, Any]] = request.get("adjustments") or request.get(
        "orderAdjustments", []
    )
    order_other_adjustment_total = Decimal("0")
    for adj in adjustments:
        amount = _to_decimal(adj.get("amount", 0))
        is_percent = adj.get("is_percent", False)
        if is_percent:
            order_other_adjustment_total += (sub_total * amount) / Decimal("100")
        else:
            order_other_adjustment_total += amount

    # ---------------------------------------------------------------------
    # Global adjustments (apply to whole order)
    # ---------------------------------------------------------------------
    global_adjustments: List[Dict[str, Any]] = request.get(
        "global_adjustments"
    ) or request.get("globalAdjustments", [])
    order_global_adjustments = Decimal("0")
    for adj in global_adjustments:
        ship_seq = adj.get("ship_group_seq_id")
        # Include only when ship_group_seq_id is None or the sentinel "_NA_"
        if ship_seq is None or ship_seq == "_NA_":
            amount = _to_decimal(adj.get("amount", 0))
            is_percent = adj.get("is_percent", False)
            if is_percent:
                order_global_adjustments += (sub_total * amount) / Decimal("100")
            else:
                order_global_adjustments += amount
        # else: explicitly excluded

    # ---------------------------------------------------------------------
    # Grand total
    # ---------------------------------------------------------------------
    grand_total = (
        sub_total
        + total_shipping
        + total_sales_tax
        + order_other_adjustment_total
        + order_global_adjustments
    )

    return {
        "sub_total": sub_total,
        "total_shipping": total_shipping,
        "total_sales_tax": total_sales_tax,
        "order_other_adjustment_total": order_other_adjustment_total,
        "order_global_adjustments": order_global_adjustments,
        "grand_total": grand_total,
    }