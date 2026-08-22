import os
import re
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from core.state import RosettaState
from core.formula_ir import extract_formula_ir_from_logic_json
from dotenv import load_dotenv

load_dotenv()
# Initialize the LLM (Gemini 1.5 Pro/Flash for code reasoning)
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.1)


# ==========================================
# HELPER: MARKDOWN EXTRACTOR
# ==========================================
def extract_code_block(text, language: str) -> str:
    """Extracts code from markdown blocks and safely handles LangChain lists."""
    if isinstance(text, list):
        text = "".join([str(block.get("text", block)) if isinstance(block, dict) else str(block) for block in text])
        
    pattern = rf"```{language}\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

# ==========================================
# 1. DISCOVERY AGENT (The Cleansing Chamber)
# ==========================================
def discovery_node(state: RosettaState) -> RosettaState:
    print(f"\n[Agent] Discovery: Analyzing legacy Java method '{state['target_method']}'...")
    
    neo4j_context_str = json.dumps(state.get("neo4j_context") or {}, indent=2)
    
    prompt = PromptTemplate.from_template("""
    You are a distinguished Principal Architect specializing in legacy modernization.
    Analyze the following Java code and extract:
    1. The pure business logic and calculation rules for method: {target_method}.
    2. At least three canonical JSON test payloads representing the input parameters this method expects.
    3. The expected output JSON response for each test payload.
    4. A structured list of formula_terms: every named output field that must appear in the response,
       each with its source Java method name and whether it is required.
    
    IMPORTANT NEO4J CONTEXT:
    You are provided with an AST graph extraction of the legacy database operations and schema properties used by this method and its dependencies.
    TREAT THIS NEO4J CONTEXT AS FACTUAL EXTRACTED EVIDENCE. 
    DO NOT invent database entities, method dependencies, or schema keys if they are already available in this context. Use the schema properties found in the graph context to build your test payloads.
    
    Neo4j Graph Context:
    {neo4j_context}
    
    Legacy Java Code:
    {java_code}
    
    Return ONLY a valid JSON object wrapped in a ```json``` block with this exact structure:
    {{
      "method_name": "{target_method}",
      "logic": "Detailed description of the calculation rules and loops",
      "mathematical_formula": "e.g. sub_total + total_shipping + total_sales_tax + ...",
      "formula_terms": [
        {{"name": "sub_total", "source_method": "getSubTotal", "required": true}},
        {{"name": "total_shipping", "source_method": "getTotalShipping", "required": true}}
      ],
      "schema_keys": ["list of main incoming payload keys like cartLines, shipGroups, etc."],
      "test_payload": {{ ...first input fields matching the Java method... }},
      "expected_output": {{ "grand_total": 137.1 }},
      "test_cases": [
          {{"name": "baseline", "payload": {{ ... }}, "expected_output": {{ ... }} }}
      ]
    }}
    """)
    
    chain = prompt | llm
    
    max_retries = 3
    parsed_json = None
    for attempt in range(max_retries):
        try:
            response = chain.invoke({
                "target_method": state["target_method"],
                "java_code": state["java_code"],
                "neo4j_context": neo4j_context_str
            })
            parsed_json = json.loads(extract_code_block(response.content, "json"))
            break
        except json.JSONDecodeError as e:
            print(f"[-] JSON parse error on attempt {attempt+1}: {e}. Retrying...")
            if attempt == max_retries - 1:
                print(f"[!] Failed to parse JSON after {max_retries} attempts.")
                print(f"Raw output: {response.content}")
                raise
                
    logic_json_str = json.dumps(parsed_json)

    # Extract formula IR so validator can run T1 without re-parsing
    formula_ir_obj = extract_formula_ir_from_logic_json(logic_json_str)
    formula_ir_dict = None
    if formula_ir_obj is not None:
        formula_ir_dict = {
            "method_name": formula_ir_obj.method_name,
            "formula": formula_ir_obj.formula,
            "formula_terms": [
                {
                    "name": t.name,
                    "source_method": t.source_method,
                    "required": t.required,
                }
                for t in formula_ir_obj.terms
            ],
        }
    
    print("[+] Discovery Complete. Business logic and dynamic schema extracted.")
    return {
        "logic_json": logic_json_str,
        "formula_ir": formula_ir_dict,
        "test_payload": parsed_json.get("test_payload", state.get("test_payload")),
        "expected_legacy_output": parsed_json.get("expected_output", {"grand_total": 10.00}),
        "test_cases": parsed_json.get("test_cases") or [{
            "name": "discovery_case",
            "payload": parsed_json.get("test_payload", state.get("test_payload", {})),
            "expected_output": parsed_json.get("expected_output", {"grand_total": 10.00}),
        }],
    }

# ==========================================
# 2. ARCHITECTURE AGENT (The Modernizer)
# ==========================================
def architecture_node(state: RosettaState) -> RosettaState:
    attempt = state.get('retry_count', 0) + 1
    print(f"\n[Agent] Architecture: Generating FastAPI service (Attempt {attempt})...")
    
    # Handle the Shadow Validation feedback loop
    feedback_section = ""
    if state.get("validation_feedback"):
        feedback_section = f"""
        WARNING: Your previous code generation failed the shadow equivalence test. 
        Analyze this error trace carefully and fix the logic or data structures:
        {state["validation_feedback"]}
        """

    # Build golden fixture contract from state (or use hardcoded defaults for getGrandTotal)
    formula_ir = state.get("formula_ir") or {}
    formula_terms = formula_ir.get("formula_terms", []) if formula_ir else []
    required_output_fields = (
        ", ".join(t["name"] for t in formula_terms if t.get("required", True)) + ", grand_total"
        if formula_terms
        else "sub_total, total_shipping, total_sales_tax, order_other_adjustment_total, order_global_adjustments, grand_total"
    )
    
    golden_input_schema = json.dumps({
        "cart_lines": [{"item_sub_total": "50.00"}],
        "ship_info": [{"ship_estimate": "10.00", "total_tax": "8.40"}],
        "adjustments": [{"amount": "-10.00", "is_percent": False, "ship_group_seq_id": None}],
        "global_adjustments": [{"amount": "2.00", "is_percent": False, "ship_group_seq_id": None}]
    }, indent=2)
    
    golden_example = json.dumps({
        "input": {
            "cart_lines": [{"item_sub_total": "120.00"}],
            "ship_info": [{"ship_estimate": "10.00", "total_tax": "8.40"}],
            "adjustments": [{"amount": "-10.00", "is_percent": False, "ship_group_seq_id": None}],
            "global_adjustments": [{"amount": "2.00", "is_percent": False, "ship_group_seq_id": None}]
        },
        "expected_output": {
            "sub_total": "120.00",
            "total_shipping": "10.00",
            "total_sales_tax": "8.40",
            "order_other_adjustment_total": "-10.00",
            "order_global_adjustments": "2.00",
            "grand_total": "130.40"
        }
    }, indent=2)

    prompt = PromptTemplate.from_template("""
    You are an elite Python Backend Architect. Your job is to convert the abstract 
    business logic and data requirements JSON below into a production-ready, pure Python function.
    
    CRITICAL ARCHITECTURAL CONSTRAINTS:
    - Generate a single pure Python function named `calculate_{target_method}`.
    - The function MUST accept exactly one argument named `request` of type `dict` (or `Any`).
    - The function MUST return a `dict`.
    - Do NOT import or use FastAPI, APIRouter, or Pydantic. Use only the Python standard library.
    - Do NOT write async functions. Use standard synchronous `def`.
    - DYNAMIC COMPUTATION RULE: Iterate through all list fields in the input. Never hardcode zero.
    - FORMULA COMPLETENESS RULE: Use every required component in the final calculation.
    - RESPONSE CONTRACT RULE: Return ALL required output fields. Even if a component is zero, include it.
    - TDD DEBUGGING RULE: If retrying, study the validation_feedback carefully — it includes the exact input, expected trace, and differences. Fix the specific bug.

    GOLDEN FIXTURE CONTRACT — your function MUST match this exactly:

    Input schema (exact keys your function will receive in `request`):
    {golden_input_schema}

    Required output fields (ALL must be present in your returned dict, even when zero):
    {required_output_fields}

    Example golden fixture (input → expected output you must reproduce):
    {golden_example}

    Computation rules derived from the golden arithmetic:
    - sub_total: sum of cart_lines[].item_sub_total (as Decimal)
    - total_shipping: sum of ship_info[].ship_estimate (as Decimal)
    - total_sales_tax: sum of ship_info[].total_tax (as Decimal)
    - order_other_adjustment_total: sum of adjustments[].amount where ship_group_seq_id is NOT None, else fixed amount if ship_group_seq_id is None
      (simpler: sum ALL adjustments[].amount that are not global — if ship_group_seq_id is explicitly null, treat as global)
    - order_global_adjustments: sum of global_adjustments[].amount (as Decimal)
    - grand_total: sub_total + total_shipping + total_sales_tax + order_other_adjustment_total + order_global_adjustments
    - All output values must be formatted as strings with 2 decimal places (e.g. "130.40").
    - Use Python's `decimal.Decimal` for all arithmetic to avoid floating-point errors.
    
    {feedback_section}
    
    Abstract Business Logic & Data Schema:
    {logic_json}
    
    Output ONLY valid Python code wrapped in a ```python``` block. Do not include markdown explanations.
    """)
    
    chain = prompt | llm
    response = chain.invoke({
        "target_method": state["target_method"],
        "logic_json": state["logic_json"],
        "feedback_section": feedback_section,
        "golden_input_schema": golden_input_schema,
        "required_output_fields": required_output_fields,
        "golden_example": golden_example,
    })
    
    pure_function_source = extract_code_block(response.content, "python")
    
    print("[+] Architecture Complete. Pure Python function generated.")
    return {
        "pure_function_source": pure_function_source,
        "candidate_source": pure_function_source,
        "generated_python": pure_function_source,
        "retry_count": attempt
    }