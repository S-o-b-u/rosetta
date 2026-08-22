from typing import TypedDict, Dict, Any, Optional

class RosettaState(TypedDict):
    # ==========================================
    # 1. INPUT & CONTEXT (Provided by CLI)
    # ==========================================
    file_path: str
    target_method: str
    java_code: str

    # ==========================================
    # 2. AGENT OUTPUTS (Populated during pipeline)
    # ==========================================
    logic_json: Optional[str]             # Output from Discovery Agent (raw JSON string)
    formula_ir: Optional[Dict[str, Any]]  # Structured formula IR extracted from logic_json

    # Pure-function-first pipeline:
    #   pure_function_source  — validated plain Python function (output of Architecture Agent)
    #   wrapped_service_source — deterministic FastAPI wrapper (output of Wrapper Node)
    pure_function_source: Optional[str]
    wrapped_service_source: Optional[str]

    # Kept for backwards-compatibility with legacy tests and java_executed adapter mode.
    # In the live pipeline, candidate_source is the same value as pure_function_source.
    candidate_source: Optional[str]
    generated_python: Optional[str]       # deprecated alias for pure_function_source

    openapi_spec: Optional[str]           # reserved for future OpenAPI generation

    # ==========================================
    # 3. SHADOW VALIDATION (For Equivalence Testing)
    # ==========================================
    test_payload: Optional[Dict[Any, Any]]              # Baseline JSON request
    expected_legacy_output: Optional[Dict[Any, Any]]    # Baseline Java JSON response
    test_cases: Optional[list[Dict[str, Any]]]          # Canonical parity fixtures
    baseline_mode: str                                  # provisional | approved | golden_file | java_executed
    baseline_command: Optional[str]                     # External legacy adapter command
    validation_results: Optional[list[Dict[str, Any]]] # Per-case parity results
    validation_passed: bool                             # True if all tiers pass
    validation_feedback: Optional[str]                  # Diff sent back to Architecture Agent

    # ==========================================
    # 4. PARITY REPORT (T1-T4 tier results)
    # ==========================================
    parity_report: Optional[Dict[str, Any]]  # Aggregated T1/T2/T3/T4 tier results

    # ==========================================
    # 5. SAFETY GUARDRAILS
    # ==========================================
    retry_count: int  # Prevents the Architecture Agent from infinite looping