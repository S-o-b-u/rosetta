from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List


def calculate_getTotalShipping(request: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate the total shipping cost by summing the `shipEstimate` values
    found in the `shipInfo` collection of the request payload.

    Parameters
    ----------
    request: dict
        Expected to contain a key `shipInfo` whose value is a list of objects,
        each having a numeric `shipEstimate` field.

    Returns
    -------
    dict
        A dictionary with a single key `total_shipping` representing the summed
        shipping cost as a float. If the input list is empty or missing, the
        total is 0.0.
    """
    ship_info: List[Dict[str, Any]] = request.get("shipInfo", [])
    if not isinstance(ship_info, list):
        # If shipInfo is not a list, treat it as empty to avoid crashes.
        ship_info = []

    total = Decimal("0")
    for item in ship_info:
        # Guard against malformed items.
        estimate = item.get("shipEstimate", 0)
        try:
            # Convert to Decimal for accurate arithmetic.
            estimate_decimal = Decimal(str(estimate))
        except (InvalidOperation, TypeError, ValueError):
            # If conversion fails, treat the estimate as zero.
            estimate_decimal = Decimal("0")
        total += estimate_decimal

    # Convert Decimal back to float for the response contract.
    return {"total_shipping": float(total)}