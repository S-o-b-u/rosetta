from decimal import Decimal

def _calculate_adjustment_amount(
    adjustment: dict,
    base_amount: Decimal,
    include_tax: bool = False,
    include_shipping: bool = False,
    tax_amount: Decimal = Decimal("0.00"),
    shipping_amount: Decimal = Decimal("0.00")
) -> Decimal:
    applicable_base = base_amount
    if include_tax:
        applicable_base += tax_amount
    if include_shipping:
        applicable_base += shipping_amount

    amount = Decimal(str(adjustment.get("amount", 0)))
    if adjustment.get("is_percent"):
        return (applicable_base * amount) / Decimal("100.00")
    return amount

def calculate_getGrandTotal(request: dict) -> dict:
    sub_total = Decimal("0.00")
    for item in request.get("cart_lines", []):
        sub_total += Decimal(str(item.get("item_sub_total", 0)))

    total_shipping = Decimal("0.00")
    total_sales_tax = Decimal("0.00")
    for ship in request.get("ship_info", []):
        total_shipping += Decimal(str(ship.get("ship_estimate", 0)))
        total_sales_tax += Decimal(str(ship.get("total_tax", 0)))

    order_other_adjustment_total = Decimal("0.00")
    for adj in request.get("adjustments", []):
        order_other_adjustment_total += _calculate_adjustment_amount(
            adj,
            base_amount=sub_total,
            include_tax=False,
            include_shipping=False
        )

    order_global_adjustments = Decimal("0.00")
    for adj in request.get("global_adjustments", []):
        ship_group = adj.get("ship_group_seq_id")
        if ship_group in (None, "_NA_"):
            order_global_adjustments += _calculate_adjustment_amount(
                adj,
                base_amount=sub_total,
                include_tax=True,
                include_shipping=True,
                tax_amount=total_sales_tax,
                shipping_amount=total_shipping
            )

    grand_total = (
        sub_total
        + total_shipping
        + total_sales_tax
        + order_other_adjustment_total
        + order_global_adjustments
    )

    return {
        "subTotal": float(sub_total),
        "totalShipping": float(total_shipping),
        "totalSalesTax": float(total_sales_tax),
        "orderOtherAdjustmentTotal": float(order_other_adjustment_total),
        "orderGlobalAdjustments": float(order_global_adjustments),
        "grand_total": float(grand_total)
    }
