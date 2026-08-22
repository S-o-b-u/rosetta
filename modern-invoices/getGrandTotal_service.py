from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(tags=["Generated Service"])


class CartLineItem(BaseModel):
    item_sub_total: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Subtotal for an individual line item in the cart."
    )


class ShipInfo(BaseModel):
    ship_estimate: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Shipping estimate for a ship group."
    )
    total_tax: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Sales tax calculated for a ship group."
    )


class OrderAdjustment(BaseModel):
    amount: Decimal = Field(
        ...,
        description="Adjustment amount (can be positive for charges or negative for discounts)."
    )
    is_percent: bool = Field(
        default=False,
        description="Indicates whether the adjustment amount is a percentage rate."
    )
    ship_group_seq_id: Optional[str] = Field(
        default=None,
        description="Associated ship group sequence identifier."
    )


class GrandTotalRequest(BaseModel):
    cart_lines: List[CartLineItem] = Field(
        default_factory=list,
        description="Line items present in the shopping cart."
    )
    ship_info: List[ShipInfo] = Field(
        default_factory=list,
        description="Shipping and tax estimates per ship group."
    )
    adjustments: List[OrderAdjustment] = Field(
        default_factory=list,
        description="Non-shipping and non-tax order-level adjustments."
    )
    global_adjustments: List[OrderAdjustment] = Field(
        default_factory=list,
        description="Global order adjustments not tied to a specific ship group."
    )


class GrandTotalResponse(BaseModel):
    sub_total: Decimal = Field(..., description="Sum of line item subtotals.")
    total_shipping: Decimal = Field(..., description="Sum of shipping estimates.")
    total_sales_tax: Decimal = Field(..., description="Sum of sales tax across ship groups.")
    order_other_adjustment_total: Decimal = Field(..., description="Calculated non-shipping/tax order adjustments.")
    order_global_adjustments: Decimal = Field(..., description="Calculated global order adjustments.")
    grand_total: Decimal = Field(..., description="Calculated grand total cost of the cart.")


def _calculate_adjustment_amount(
    adjustment: OrderAdjustment,
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

    if adjustment.is_percent:
        return (applicable_base * adjustment.amount) / Decimal("100.00")
    return adjustment.amount


@router.post(
    "/calculate-grand-total",
    response_model=GrandTotalResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Grand Total",
    description="Calculate the final total cost of the shopping cart including line item totals, shipping costs, sales tax, and applicable order adjustments."
)
async def calculate_grand_total(request: GrandTotalRequest) -> GrandTotalResponse:
    sub_total = sum((item.item_sub_total for item in request.cart_lines), Decimal("0.00"))
    total_shipping = sum((ship.ship_estimate for ship in request.ship_info), Decimal("0.00"))
    total_sales_tax = sum((ship.total_tax for ship in request.ship_info), Decimal("0.00"))

    order_other_adjustment_total = sum(
        (
            _calculate_adjustment_amount(
                adj,
                base_amount=sub_total,
                include_tax=False,
                include_shipping=False
            )
            for adj in request.adjustments
        ),
        Decimal("0.00")
    )

    order_global_adjustments = sum(
        (
            _calculate_adjustment_amount(
                adj,
                base_amount=sub_total,
                include_tax=True,
                include_shipping=True,
                tax_amount=total_sales_tax,
                shipping_amount=total_shipping
            )
            for adj in request.global_adjustments
            if adj.ship_group_seq_id in (None, "_NA_")
        ),
        Decimal("0.00")
    )

    grand_total = (
        sub_total
        + total_shipping
        + total_sales_tax
        + order_other_adjustment_total
        + order_global_adjustments
    )

    return GrandTotalResponse(
        sub_total=sub_total,
        total_shipping=total_shipping,
        total_sales_tax=total_sales_tax,
        order_other_adjustment_total=order_other_adjustment_total,
        order_global_adjustments=order_global_adjustments,
        grand_total=grand_total
    )