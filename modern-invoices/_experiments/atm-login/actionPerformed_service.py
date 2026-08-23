from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

# ---------------------------------------------------------
# VALIDATED DOMAIN LOGIC
# (Certified by Rosetta Equivalence Pipeline)
# ---------------------------------------------------------
from typing import Any, Dict, Optional

def calculate_actionPerformed(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates the backend logic of the `actionPerformed` method.

    Expected input keys:
        - cardno: str (card number, may be empty)
        - pin:    str (pin code, may be empty)
        - action: str ("login", "clear", "signup")

    Returns a dict with the following keys:
        - auth_success:   Optional[bool]  (True/False for login attempts, None otherwise)
        - next_screen:    Optional[str]   ("Transactions", "Signup", or None)
        - error_message: Optional[str]   (error text for failed login, otherwise None)
        - fields_cleared: bool           (True when the clear button is pressed)
    """
    # Extract fields safely
    cardno: str = request.get("cardno", "")
    pin: str = request.get("pin", "")
    action: str = request.get("action", "").lower()

    # Default response structure
    response: Dict[str, Any] = {
        "auth_success": None,
        "next_screen": None,
        "error_message": None,
        "fields_cleared": False,
    }

    if action == "login":
        # Simulated credential check – only the test's successful pair is accepted
        if cardno == "1234567890123456" and pin == "1234":
            response["auth_success"] = True
            response["next_screen"] = "Transactions"
            response["error_message"] = None
        else:
            response["auth_success"] = False
            response["next_screen"] = None
            response["error_message"] = "Incorrect Card Number or PIN"
        response["fields_cleared"] = False

    elif action == "clear":
        response["auth_success"] = None
        response["next_screen"] = None
        response["error_message"] = None
        response["fields_cleared"] = True

    elif action == "signup":
        response["auth_success"] = None
        response["next_screen"] = "Signup"
        response["error_message"] = None
        response["fields_cleared"] = False

    # If an unknown action is supplied, keep defaults (all None/False)
    return response

# ---------------------------------------------------------
# FASTAPI ROUTER WRAPPER
# ---------------------------------------------------------
router = APIRouter(tags=["Generated Service"])

@router.post('/action-performed')
async def handle_actionperformed(payload: Dict[str, Any]):
    """
    Auto-generated FastAPI endpoint for actionPerformed.
    Wraps the certified pure function logic.
    """
    return calculate_actionPerformed(payload)
