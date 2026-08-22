def _calc_adj(adj: dict, base: float) -> float:
    amt = float(adj.get("amount", 0.0))
    if adj.get("is_percent") or adj.get("isPercent") or adj.get("isPercentage"):
        return (base * amt) / 100.0
    return amt


def calculate_getGrandTotal(request: dict) -> dict:
    if not isinstance(request, dict):
        request = {}

    cart_lines = request.get("cartLines")
    if cart_lines is None:
        cart_lines = request.get("cart_lines", [])

    ship_info = request.get("shipInfo")
    if ship_info is None:
        ship_info = request.get("ship_info")
    if ship_info is None:
        ship_info = request.get("shipInfoList", [])

    adjustments = request.get("adjustments")
    if adjustments is None:
        adjustments = []

    global_adjustments = request.get("globalAdjustments")
    if global_adjustments is None:
        global_adjustments = request.get("global_adjustments", [])
    if global_adjustments is None:
        global_adjustments = []

    # 1. sub_total = sum of all cartLines itemSubTotal
    sub_total = 0.0
    for line in cart_lines:
        if isinstance(line, dict):
            val = line.get("itemSubTotal")
            if val is None:
                val = line.get("item_sub_total")
            if val is None:
                qty = float(line.get("quantity") or line.get("qty") or 0.0)
                price = float(line.get("price") or line.get("unitPrice") or line.get("unit_price") or 0.0)
                val = qty * price
            sub_total += float(val or 0.0)

    # 2. total_shipping = sum of all shipInfo shipEstimate
    # 3. total_sales_tax = sum of all shipInfo totalTax
    total_shipping = 0.0
    total_sales_tax = 0.0
    for info in ship_info:
        if isinstance(info, dict):
            ship_val = info.get("shipEstimate")
            if ship_val is None:
                ship_val = info.get("ship_estimate", 0.0)
            total_shipping += float(ship_val or 0.0)

            tax_val = info.get("totalTax")
            if tax_val is None:
                tax_val = info.get("total_tax", 0.0)
            total_sales_tax += float(tax_val or 0.0)

    # 4. order_other_adjustment_total = sum of all adjustments using base = sub_total
    order_other_adjustment_total = 0.0
    for adj in adjustments:
        if isinstance(adj, dict):
            order_other_adjustment_total += _calc_adj(adj, sub_total)

    # 5. order_global_adjustments = sum of all globalAdjustments using base = sub_total + total_shipping + total_sales_tax
    # ONLY include if shipGroupSeqId is null (None) or "_NA_"
    global_base = sub_total + total_shipping + total_sales_tax
    order_global_adjustments = 0.0
    for adj in global_adjustments:
        if isinstance(adj, dict):
            seq_id = adj.get("shipGroupSeqId")
            if "shipGroupSeqId" not in adj and "ship_group_seq_id" in adj:
                seq_id = adj.get("ship_group_seq_id")
            if seq_id is None or seq_id == "_NA_":
                order_global_adjustments += _calc_adj(adj, global_base)

    # 6. grand_total = sum of all 5 components above
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