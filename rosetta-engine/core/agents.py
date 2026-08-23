import os
import re
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from core.state import RosettaState
from core.formula_ir import extract_formula_ir_from_logic_json
from dotenv import load_dotenv

load_dotenv()
from langchain_openai import ChatOpenAI

# Initialize the primary LLM
primary_llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.1)

# Wire up Cerebras fallback if the API key is present
if os.getenv("CEREBRAS_API_KEY"):
    fallback_llm = ChatOpenAI(
        model="llama3.1-70b",
        api_key=os.getenv("CEREBRAS_API_KEY"),
        base_url="https://api.cerebras.ai/v1",
        temperature=0.1,
    )
    llm = primary_llm.with_fallbacks([fallback_llm])
else:
    llm = primary_llm


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
    source_lang      = state.get("source_lang", "java").title()
    source_framework = state.get("source_framework", "ofbiz")
    print(f"\n[Agent] Discovery: Analyzing legacy {source_lang} method '{state['target_method']}'...")

    neo4j_context_str = json.dumps(state.get("neo4j_context") or {}, indent=2)
    
    migrated_deps = state.get("migrated_dependencies", {})
    deps_str = ""
    if migrated_deps:
        deps_str = "\n    ALREADY MIGRATED DEPENDENCIES (Use their strict contract behavior, do not invent it):\n    " + json.dumps(migrated_deps, indent=4).replace("\n", "\n    ")

    # ----------------------------------------------------------------
    # Phase 3: Framework-specific boilerplate instructions
    # These tell the LLM *what to ignore* so it focuses on
    # pure business logic regardless of the source framework.
    # ----------------------------------------------------------------
    _framework_boilerplate = {
        "ofbiz": (
            "You are analyzing Apache OFBiz enterprise Java code. "
            "Strip away all OFBiz-specific boilerplate: GenericDelegator, LocalDispatcher, "
            "DispatchContext, GenericValue, EntityQuery, ServiceUtil.returnSuccess/returnError. "
            "Focus ONLY on the business rules, calculations, and data transformations."
        ),
        "swing_java": (
            "You are analyzing a legacy Java Swing desktop application. "
            "Strip away all Swing/AWT UI boilerplate: ActionEvent, ActionListener, JButton, "
            "JFrame, JTextField, JLabel, JOptionPane, setLayout, addActionListener, getContentPane. "
            "Focus ONLY on the business logic: what data is read from form fields, "
            "what database operations are performed via JDBC (Conn class), "
            "what business rules/validations are applied, and what the outcome is. "
            "IMPORTANT: If there are raw SQL queries (e.g., `select * from ...`), preserve the EXACT SQL string in the 'logic' description. Do not abstract it into English. "
            "CRITICAL — formula_terms must list ONLY the OUTPUT fields returned by the function "
            "(e.g. auth_success, next_screen, error_message). "
            "Do NOT include input fields (e.g. cardno, pin, action) in formula_terms — "
            "those belong in schema_keys only."
        ),
    }
    framework_instruction = _framework_boilerplate.get(
        source_framework,
        f"Strip away framework-specific boilerplate for '{source_framework}'. Focus on pure business logic."
    )

    prompt = PromptTemplate.from_template("""
    You are a distinguished Principal Architect specializing in legacy modernization.
    
    FRAMEWORK CONTEXT:
    {framework_instruction}
    
    Analyze the following {source_lang} code and extract:
    1. The pure business logic and calculation rules for method: {target_method}.
    2. At least three canonical JSON test payloads representing the input parameters this method expects.
    3. The expected output JSON response for each test payload.
    4. A structured list of formula_terms: every named output field that must appear in the response,
       each with its source {source_lang} method name and whether it is required.
       
    IMPORTANT NEO4J CONTEXT:
    You are provided with an AST graph extraction of the legacy database operations and schema properties used by this method and its dependencies.
    TREAT THIS NEO4J CONTEXT AS FACTUAL EXTRACTED EVIDENCE. 
    DO NOT invent database entities, method dependencies, or schema keys if they are already available in this context. Use the schema properties found in the graph context to build your test payloads.
    {deps_str}
    
    Neo4j Graph Context:
    {neo4j_context}
    
    Legacy {source_lang} Code:
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
      "expected_output": {{ "sub_total": 100.0, "grand_total": 137.1 }},
      "test_cases": [
          {{"name": "baseline", "payload": {{ ... }}, "expected_output": {{ ... }} }}
      ]
    }}
    
    CRITICAL JSON FORMATTING RULES:
    1. Do NOT include trailing commas anywhere in the JSON (e.g., before closing braces or brackets).
    2. Properly escape all internal double quotes inside string fields (like the "logic" field).
    3. Output ONLY the raw JSON object inside the markdown code block. Do not output any conversational text before or after it.
    """)

    chain = prompt | llm

    max_retries = 3
    parsed_json = None
    for attempt in range(max_retries):
        try:
            response = chain.invoke({
                "target_method":       state["target_method"],
                "java_code":           state["java_code"],
                "neo4j_context":       neo4j_context_str,
                "source_lang":         source_lang,
                "framework_instruction": framework_instruction,
                "deps_str":            deps_str,
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
    print(f"\n[Agent] Architecture: Generating pure python function (Attempt {attempt})...")
    
    # Handle the Shadow Validation feedback loop
    feedback_section = ""
    if state.get("validation_feedback"):
        feedback_section = f"""
        WARNING: Your previous code generation failed the shadow equivalence test. 
        Analyze this error trace carefully and fix the logic or data structures:
        {state["validation_feedback"]}
        """

    # ------------------------------------------------------------------
    # Build a golden contract section if a manifest is available.
    # Sources required fields from the fixture's expected_output keys —
    # this includes the final aggregated result (e.g. "grand_total") which
    # formula_terms does NOT list. Injects targeted edge-case examples for
    # the two business rules the LLM most often gets wrong:
    #   - is_percent=True adjustment calculation
    #   - ship_group_seq_id exclusion rule
    # ------------------------------------------------------------------
    golden_contract_section = ""
    try:
        import json as _json
        from core.golden import GoldenFileProvider, GoldenFileNotFoundError
        provider = GoldenFileProvider(state["target_method"])
        all_fixtures = provider.all_fixtures()

        if all_fixtures:
            # Source the required field list from any fixture's expected_output.
            required_fields = list(all_fixtures[0].expected_output.keys())
            fields_str = "\n    ".join(f'- "{f}"' for f in required_fields)

            # Build a lookup by fixture_id for targeted injection.
            fx_map = {fx.fixture_id: fx for fx in all_fixtures}

            def _fmt(fx):
                """Format one fixture as an escaped worked example block."""
                esc = lambda s: _json.dumps(s).replace("{", "{{").replace("}", "}}")
                return (
                    f"  Example — {fx.description}:\n"
                    f"    Input:    {esc(fx.input)}\n"
                    f"    Expected: {esc(fx.expected_output)}\n"
                    f"    Trace:    {esc(fx.arithmetic_trace)}"
                )

            # Prefer the two hardest edge-case fixtures; fall back gracefully.
            example_ids = ["case_05_percentage_adjustment", "case_07_ship_group_excluded"]
            chosen = [fx_map[eid] for eid in example_ids if eid in fx_map]
            if not chosen:
                chosen = all_fixtures[-2:] if len(all_fixtures) >= 2 else all_fixtures

            examples_str = "\n\n".join(_fmt(fx) for fx in chosen)

            golden_contract_section = f"""
    GOLDEN CONTRACT (NON-NEGOTIABLE): The returned dict MUST contain EXACTLY these
    snake_case keys — no aliases, no renames, no omissions — and ALL must be present
    even when their value is zero:
    {fields_str}
    Omitting any key or using a wrong name causes immediate validation failure.

    CRITICAL BUSINESS RULES (these are the rules the LLM most often gets wrong):
    1. PERCENTAGE ADJUSTMENTS: When `is_percent` is True for an adjustment, the amount
       is a percentage of sub_total. Compute: (sub_total * amount) / 100.
       Do NOT use the raw amount value directly.
    2. SHIP GROUP EXCLUSION: Global adjustments where `ship_group_seq_id` is NOT None
       AND NOT "_NA_" must contribute ZERO to `order_global_adjustments`. Only include
       adjustments where ship_group_seq_id is None or exactly equal to "_NA_".

    CONCRETE WORKED EXAMPLES (study these carefully — they show the exact edge cases):
{examples_str}
"""
    except Exception:
        pass  # No manifest found — proceed without golden contract

    source_framework = state.get("source_framework", "ofbiz")
    
    migrated_deps = state.get("migrated_dependencies", {})
    deps_str = ""
    if migrated_deps:
        deps_str = "\n    ALREADY MIGRATED DEPENDENCIES (If your logic calls these, you MUST use their exact Python signatures and behaviors):\n    " + json.dumps(migrated_deps, indent=4).replace("\n", "\n    ")
    
    framework_specific_rules = ""
    if source_framework == "swing_java":
        framework_specific_rules = """
    - SCOPED SIDE-EFFECTS RULE (swing_java): If the business logic explicitly describes executing a database query where the query *is* the core business decision (e.g., authentication, balance checks), you are PERMITTED to `import sqlite3` and execute the query directly inside the function against `bankmanagementsystem.db`. For other methods where data is just fetched and then calculated, keep the function pure.
    - SQL INJECTION GUARDRAIL (NON-NEGOTIABLE): If you write database access code, you MUST rewrite any legacy string-concatenation SQL (e.g. `cardno = '"+cardno+"'`) into parameterized queries (e.g. `cursor.execute("SELECT ... WHERE cardno = ?", (cardno,))`) to prevent SQL injection vulnerabilities.
        """

    safe_method_name = state['target_method'].replace("<", "").replace(">", "").replace("-", "_")
    prompt = PromptTemplate.from_template("""
    You are an elite Python Backend Architect. Your job is to convert the abstract 
    business logic and data requirements JSON below into a production-ready, pure Python function (unless framework rules permit side-effects).
    
    CRITICAL ARCHITECTURAL CONSTRAINTS:
    - Generate a single pure Python function named `calculate_{safe_method_name}`.
    - The function MUST accept exactly one argument named `request` of type `dict` (or `Any`).
    - The function MUST return a `dict`.
    - Do NOT import or use FastAPI, APIRouter, or Pydantic. Use only the Python standard library.
    - Do NOT write async functions. Use standard synchronous `def`.
    - DYNAMIC COMPUTATION RULE: Look at the input payload structure inside the JSON. If it contains list or array fields, your Python code MUST iterate through those lists, extract numeric values, and compute actual sums. Never return hardcoded zero values if input lines exist.
    - PYTHON SUM QUIRK (CRITICAL): If you use `sum()` on a generator or list comprehension, you MUST provide `start=Decimal('0')` (e.g. `sum(..., Decimal('0'))`). Otherwise, Python defaults to returning the integer `0` for empty iterables, which crashes Decimal `.quantize()` calls downstream.
    - FORMULA COMPLETENESS RULE: If the business logic contains a formula or multiple output components, use every required component in the final calculation. Do not return one component as the grand total.
    - RESPONSE CONTRACT RULE: Return all output fields described by the business logic, using stable snake_case names. Preserve every component even when its value is zero.
    - TDD DEBUGGING RULE: If you are retrying because a previous attempt failed validation, look extremely closely at the `validation_feedback`. The feedback will now include the exact `Input Payload` that caused the failure, the legacy `Expected Trace` (intermediate math steps), and the specific `Differences`. Use this concrete data to trace your code's execution, identify exactly why your logic calculated the wrong value for that payload, and fix the bug in your next version.
    {framework_specific_rules}
    
    {golden_contract_section}
    
    {feedback_section}
    {deps_str}
    
    Abstract Business Logic & Data Schema:
    {logic_json}
    
    Output ONLY valid Python code wrapped in a ```python``` block. Do not include markdown explanations.
    """)
    
    chain = prompt | llm
    response = chain.invoke({
        "target_method": state["target_method"],
        "safe_method_name": safe_method_name,
        "logic_json": state["logic_json"],
        "feedback_section": feedback_section,
        "golden_contract_section": golden_contract_section,
        "framework_specific_rules": framework_specific_rules,
        "deps_str": deps_str,
    })
    
    pure_function_source = extract_code_block(response.content, "python")
    
    print("[+] Architecture Complete. Pure Python function generated.")
    return {
        "pure_function_source": pure_function_source,
        "candidate_source": pure_function_source,
        "generated_python": pure_function_source,
        "retry_count": attempt
    }