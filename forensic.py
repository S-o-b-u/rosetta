import os
import sys
import json
import traceback

engine_path = os.path.abspath("rosetta-engine")
sys.path.insert(0, engine_path)

from core.graph import rosetta_pipeline

def run_investigation():
    file_path = "ofbiz-framework/applications/order/src/main/java/org/apache/ofbiz/order/shoppingcart/ShoppingCart.java"
    
    with open(file_path, "r", encoding="utf-8") as f:
        full_java = f.read()
        
    from server import _extract_java_method
    java_code = _extract_java_method(full_java, "getGrandTotal")
        
    initial_state = {
        "migration_id": "forensic-investigation-123",
        "file_path": file_path,
        "target_method": "getGrandTotal",
        "java_code": java_code,
        "test_payload": {},
        "expected_legacy_output": {},
        "formula_ir": None,
        "pure_function_source": None,
        "wrapped_service_source": None,
        "candidate_source": None,
        "test_cases": None,
        "baseline_mode": "provisional",
        "baseline_command": None,
        "validation_results": None,
        "parity_report": None,
        "retry_count": 0,
    }

    try:
        attempts = []
        for chunk in rosetta_pipeline.stream(initial_state):
            for node_name, state_update in chunk.items():
                if node_name == "architecture_agent":
                    attempts.append({
                        "generated_python": state_update.get("generated_python", "")
                    })
                if node_name == "validator":
                    attempts[-1]["validation_feedback"] = state_update.get("validation_feedback", "")
                    attempts[-1]["validation_results"] = state_update.get("validation_results", [])
                    attempts[-1]["parity_report"] = state_update.get("parity_report", {})
                    
        # Dump the investigation data
        with open("forensic_output.json", "w", encoding="utf-8") as f:
            json.dump({
                "attempts": attempts
            }, f, indent=2, default=str)
            
        print("Forensic investigation complete. Data saved to forensic_output.json")
        
    except Exception as e:
        print(f"Error during execution: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_investigation()
