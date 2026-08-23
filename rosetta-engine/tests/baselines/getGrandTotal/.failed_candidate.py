from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List


def calculate_getGrandTotal(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute order totals according to the business rules described in the prompt.
    All monetary values are handled as Decimals and returned as strings with two
    decimal places.
    """
    # Helper to safely convert values to Decimal
    def to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    # ---------- sub_total ----------
    cart_lines: List[Dict[str, Any]] = request.get("cartLines", [])
    sub_total = sum(
        (
            to_decimal(line["item_sub_total"])
            if "item_sub_total" in line
            else to_decimal(line.get("quantity", 0))
            * to_decimal(line.get("unitPrice", 0))
        )
        for line in cart_lines
    , Decimal("0"))

    # ---------- total_shipping ----------
    ship_groups: List[Dict[str, Any]] = request.get("shipGroups", [])
    total_shipping = sum(
        (
            to_decimal(group["ship_estimate"])
            if "ship_estimate" in group
            else to_decimal(group.get("shippingCost", 0))
        )
        for group in ship_groups
    , Decimal("0"))

    # ---------- total_sales_tax ----------
    total_sales_tax = sum(
        (
            to_decimal(group["total_tax"])
            if "total_tax" in group
            else to_decimal(group.get("salesTax", 0))
        )
        for group in ship_groups
    , Decimal("0"))

    # ---------- order_other_adjustment_total ----------
    adjustments: List[Dict[str, Any]] = request.get("adjustments", [])
    other_adj_total = Decimal("0")
    for adj in adjustments:
        amount = to_decimal(adj.get("amount", 0))
        if adj.get("is_percent") is True:
            # percentage of sub_total
            adj_amount = (sub_total * amount) / Decimal("100")
        else:
            adj_amount = amount
        other_adj_total += adj_amount

    # ---------- order_global_adjustments ----------
    global_adjustments: List[Dict[str, Any]] = request.get("globalAdjustments", [])
    global_adj_total = Decimal("0")
    for adj in global_adjustments:
        ship_seq = adj.get("ship_group_seq_id")
        # Include only if ship_seq is None or exactly "_NA_"
        if ship_seq is not None and ship_seq != "_NA_":
            continue
        amount = to_decimal(adj.get("amount", 0))
        if adj.get("is_percent") is True:
            adj_amount = (sub_total * amount) / Decimal("100")
        else:
            adj_amount = amount
        global_adj_total += adj_amount

    # ---------- grand_total ----------
    grand_total = (
        sub_total
        + total_shipping
        + total_sales_tax
        + other_adj_total
        + global_adj_total
    )

    # Format all Decimals to string with two decimal places
    def fmt(value: Decimal) -> str:
        return str(value.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP))

    return {
        "sub_total": fmt(sub_total),
        "total_shipping": fmt(total_shipping),
        "total_sales_tax": fmt(total_sales_tax),
        "order_other_adjustment_total": fmt(other_adj_total),
        "order_global_adjustments": fmt(global_adj_total),
        "grand_total": fmt(grand_total),
    }