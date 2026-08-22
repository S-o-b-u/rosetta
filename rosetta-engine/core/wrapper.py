"""
wrapper.py — Deterministic post-validation node for FastAPI wrapping.

This node runs only after the Validator confirms the pure Python function is correct.
It takes the validated logic and wraps it in a standard, production-ready FastAPI router
using a fixed template — completely eliminating LLM variability from the API surface.
"""

from core.state import RosettaState

from core.state import RosettaState
from plugins.target.fastapi_generator import FastAPIGenerator
from plugins.target.express_generator import ExpressGenerator

SUPPORTED_TARGET_FRAMEWORKS = {
    "fastapi": FastAPIGenerator,
    "express": ExpressGenerator
}

def wrapper_node(state: RosettaState) -> RosettaState:
    target_framework = state.get("target_framework", "fastapi")
    print(f"\n[Node] Wrapper: Formatting certified function '{state['target_method']}' into {target_framework} service...")
    
    GeneratorClass = SUPPORTED_TARGET_FRAMEWORKS.get(target_framework.lower())
    if not GeneratorClass:
        print(f"[!] MIGRATION FAILED — Unsupported target framework: {target_framework}")
        return {"validation_passed": False, "validation_feedback": f"Unsupported target framework: {target_framework}"}
        
    func_source = state.get("pure_function_source") or state.get("generated_python")
    method = state["target_method"]
    
    try:
        generator = GeneratorClass()
        service_source = generator.generate_service_code(func_source, method)
        route_path = generator.route_prefix_for(method)
        ext = generator.file_extension() if hasattr(generator, "file_extension") else ".py"
        entry_cmd = generator.entry_command() if hasattr(generator, "entry_command") else "python"
        print(f"[+] Wrapper Complete. {target_framework} service created for {route_path}")
        return {
            "wrapped_service_source": service_source,
            "service_extension": ext,
            "entry_command": entry_cmd,
        }
    except Exception as e:
        print(f"[!] MIGRATION FAILED — {target_framework} generator failed: {e}")
        return {"validation_passed": False, "validation_feedback": f"{target_framework} generator failed: {e}"}
