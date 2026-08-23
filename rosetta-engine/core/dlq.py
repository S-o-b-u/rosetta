import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from core.state import RosettaState

def write_dlq(
    method_fqn: str,
    file_path: str,
    reason_category: str,
    state: RosettaState,
    blocked_on: Optional[str] = None
) -> None:
    """
    Writes a failed migration attempt to the Dead Letter Queue (DLQ).
    
    reason_category should be one of:
      - "validation_failure"
      - "dependency_unresolved" 
      - "provider_error"
    """
    dlq_dir = os.path.join(state.get("output", "./modern-invoices"), "_dlq")
    os.makedirs(dlq_dir, exist_ok=True)
    
    # We may not have parity_report or validation_results if it failed early (e.g. provider error or dependency)
    parity_report = state.get("parity_report", {})
    attempts = state.get("validation_results", [])
    
    dlq_entry = {
        "method": method_fqn,
        "file_path": file_path,
        "reason_category": reason_category,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "attempts": attempts,
        "parity_report": parity_report,
        "blocked_on": blocked_on
    }
    
    safe_method_name = method_fqn.replace("<", "").replace(">", "").replace("-", "_").replace(".", "_")
    output_path = os.path.join(dlq_dir, f"{safe_method_name}_failure.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dlq_entry, f, indent=2)
        
    print(f"[!] Logged {method_fqn} to DLQ -> {output_path} (Reason: {reason_category})")
