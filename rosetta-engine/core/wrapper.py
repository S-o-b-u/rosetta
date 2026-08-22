"""
wrapper.py — Deterministic post-validation node for FastAPI wrapping.

This node runs only after the Validator confirms the pure Python function is correct.
It takes the validated logic and wraps it in a standard, production-ready FastAPI router
using a fixed template — completely eliminating LLM variability from the API surface.
"""

from core.state import RosettaState

# The standard deterministic template for wrapping a pure calculation function
# into a production FastAPI router with a Pydantic model.
SERVICE_TEMPLATE = """\
from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

# ---------------------------------------------------------
# VALIDATED DOMAIN LOGIC
# (Certified by Rosetta Equivalence Pipeline)
# ---------------------------------------------------------
{func_source}

# ---------------------------------------------------------
# FASTAPI ROUTER WRAPPER
# ---------------------------------------------------------
router = APIRouter(tags=["Generated Service"])

class {model_name}Request(BaseModel):
    payload: Dict[str, Any]
    
    # Accept arbitrary payload fields to match the legacy signature
    class Config:
        extra = "allow"

@{route_decorator}
async def handle_{method_lower}(request: {model_name}Request):
    \"\"\"
    Auto-generated FastAPI endpoint for {method}.
    Wraps the certified pure function logic.
    \"\"\"
    # Pass the entire Pydantic model dump (including extra fields) to the function
    return {func_name}(request.model_dump())
"""

def wrapper_node(state: RosettaState) -> RosettaState:
    print(f"\\n[Node] Wrapper: Formatting certified function '{state['target_method']}' into FastAPI service...")
    
    func_source = state.get("pure_function_source") or state.get("generated_python")
    method = state["target_method"]
    method_lower = method.lower()
    
    # Auto-generate a clean route path (e.g., getGrandTotal -> /grand-total)
    route_path = method
    if route_path.startswith("get"):
        route_path = route_path[3:]
    elif route_path.startswith("calculate"):
        route_path = route_path[9:]
    
    # Convert PascalCase to kebab-case
    import re
    route_path = re.sub(r'(?<!^)(?=[A-Z])', '-', route_path).lower()
    route_path = f"/{route_path}"
    
    func_name = f"calculate_{method}"
    model_name = method[0].upper() + method[1:]
    
    service_source = SERVICE_TEMPLATE.format(
        func_source=func_source,
        method=method,
        method_lower=method_lower,
        route_decorator=f"router.post('{route_path}')",
        func_name=func_name,
        model_name=model_name,
    )
    
    print(f"[+] Wrapper Complete. FastAPI service created for {route_path}")
    return {"wrapped_service_source": service_source}
