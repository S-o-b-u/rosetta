from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

# ---------------------------------------------------------
# VALIDATED DOMAIN LOGIC
# (Certified by Rosetta Equivalence Pipeline)
# ---------------------------------------------------------
from typing import Any, Dict, List


def calculate_getSubTotal(request: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate the subtotal of a shopping cart.

    Parameters
    ----------
    request: dict
        Expected to contain a key ``cartLines`` whose value is a list of
        dictionaries. Each dictionary should have an ``itemSubTotal`` field
        holding a numeric value (int or float).

    Returns
    -------
    dict
        A dictionary with a single key ``sub_total`` representing the sum of
        all ``itemSubTotal`` values. If ``cartLines`` is missing or empty,
        the subtotal is ``0.0``.
    """
    cart_lines: List[Dict[str, Any]] = request.get("cartLines", [])
    total = 0.0

    for line in cart_lines:
        # Safely extract a numeric subtotal; ignore non‑numeric or missing values.
        value = line.get("itemSubTotal", 0)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total += float(value)

    return {"sub_total": total}

# ---------------------------------------------------------
# FASTAPI ROUTER WRAPPER
# ---------------------------------------------------------
router = APIRouter(tags=["Generated Service"])

@router.post('/sub-total')
async def handle_getsubtotal(payload: Dict[str, Any]):
    """
    Auto-generated FastAPI endpoint for getSubTotal.
    Wraps the certified pure function logic.
    """
    return calculate_getSubTotal(payload)
