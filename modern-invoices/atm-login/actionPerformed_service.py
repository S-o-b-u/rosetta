from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

# ---------------------------------------------------------
# VALIDATED DOMAIN LOGIC
# (Certified by Rosetta Equivalence Pipeline)
# ---------------------------------------------------------
import sqlite3
from typing import Any, Dict, Optional

def calculate_actionPerformed(request: Dict[str, Any]) -> Dict[str, Optional[Any]]:
    """
    Processes the simulated UI action based on the provided request payload.

    Expected keys in ``request``:
        - "cardno": str (card number, used only for login)
        - "pin": str (PIN, used only for login)
        - "action": str, one of {"login", "clear", "signup"}

    Returns a dict with the following keys (always present):
        - "auth_success": bool | None
        - "next_screen": str | None
        - "error_message": str | None
    """
    # Initialise the response with explicit nulls
    response: Dict[str, Optional[Any]] = {
        "auth_success": None,
        "next_screen": None,
        "error_message": None,
    }

    action = request.get("action", "").strip().lower()

    if action == "login":
        cardno = request.get("cardno", "")
        pin = request.get("pin", "")

        # Defensive: if either credential is missing, treat as failed login
        if not cardno or not pin:
            response["auth_success"] = False
            response["error_message"] = "Incorrect Card Number or PIN"
            return response

        # Perform a safe, parameterised query against the SQLite DB
        try:
            conn = sqlite3.connect("bankmanagementsystem.db")
            cursor = conn.cursor()
            query = "SELECT 1 FROM login WHERE cardno = ? AND pin = ? LIMIT 1"
            cursor.execute(query, (cardno, pin))
            row = cursor.fetchone()
        finally:
            # Ensure resources are released even if an exception occurs
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        if row:
            response["auth_success"] = True
            response["next_screen"] = "Transactions"
        else:
            response["auth_success"] = False
            response["error_message"] = "Incorrect Card Number or PIN"

    elif action == "clear":
        # No state change required; all fields remain null as initialised
        pass

    elif action == "signup":
        response["next_screen"] = "Signup"

    # For any unrecognised action we simply return the default null-filled response
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
