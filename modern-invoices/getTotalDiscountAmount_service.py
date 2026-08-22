from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

# ---------------------------------------------------------
# VALIDATED DOMAIN LOGIC
# (Certified by Rosetta Equivalence Pipeline)
# ---------------------------------------------------------
def calculate_getTotalDiscountAmount(request):
    """
    Returns the value of the 'totalDiscountAmount' field from the input payload.

    Parameters
    ----------
    request : dict
        Input payload expected to contain the key 'totalDiscountAmount'.

    Returns
    -------
    dict
        A dictionary with a single key 'totalDiscountAmount' mirroring the input value.
        If the key is missing, the value defaults to 0.0.
    """
    # Extract the required field, defaulting to 0.0 if absent.
    total_discount = request.get("totalDiscountAmount", 0.0)

    # Preserve the exact field name and return it in a new dict.
    return {"totalDiscountAmount": total_discount}

# ---------------------------------------------------------
# FASTAPI ROUTER WRAPPER
# ---------------------------------------------------------
router = APIRouter(tags=["Generated Service"])

@router.post('/total-discount-amount')
async def handle_gettotaldiscountamount(payload: Dict[str, Any]):
    """
    Auto-generated FastAPI endpoint for getTotalDiscountAmount.
    Wraps the certified pure function logic.
    """
    return calculate_getTotalDiscountAmount(payload)
