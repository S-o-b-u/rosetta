# Rosetta Migration Engine — Developer README

> **For:** Backend developer onboarding
> **Status:** Active development — pipeline functional, validator partially failing
> **Last updated:** 2026-08-23

---

## What Is Rosetta?

Rosetta is an **AI-powered legacy code modernisation engine**. It takes a Java method from a monolith (currently Apache OFBiz), extracts its business logic via AST parsing and an LLM, generates equivalent modern Python code, and then validates correctness through a multi-tier equivalence testing framework — all fully automated.

The current target under test is:
```
ShoppingCart.java -> getGrandTotal()
```

---

## Repository Structure

```
rosetta/
+-- rosetta-engine/               # Python backend (FastAPI + LangGraph)
¦   +-- server.py                 # FastAPI HTTP server (SSE streaming)
¦   +-- core/
¦   ¦   +-- graph.py              # LangGraph pipeline definition
¦   ¦   +-- agents.py             # Discovery + Architecture LLM agents  ? PRIMARY FILE
¦   ¦   +-- validator.py          # Multi-tier equivalence validator (T1/T3/Shadow)
¦   ¦   +-- formula_ir.py         # Formula IR + T1 schema check
¦   ¦   +-- equivalence.py        # JSON normalisation + diff engine
¦   ¦   +-- golden.py             # Golden fixture file loader
¦   ¦   +-- parity_report.py      # Tier result aggregator + console renderer
¦   ¦   +-- state.py              # LangGraph TypedDict state schema
¦   ¦   +-- wrapper.py            # Wraps the pure function into a FastAPI service
¦   +-- parsers/
¦   ¦   +-- ast_ingester.py       # Java AST parser ? Neo4j graph
¦   +-- tests/
¦       +-- baselines/
¦       ¦   +-- getGrandTotal/    # Golden fixtures (7 JSON files + _manifest.json)
¦       +-- test_equivalence.py
¦       +-- test_golden_equivalence.py
¦       +-- test_property_invariants.py
¦
+-- rosetta-workspace/            # Next.js frontend (Sandbox UI)
¦
+-- ofbiz-framework/              # Apache OFBiz source (local monolith under test)
¦   +-- applications/order/src/main/java/org/apache/ofbiz/order/shoppingcart/
¦       +-- ShoppingCart.java     # Primary target
¦
+-- .env                          # GROQ_API_KEY
+-- .venv/                        # Python virtualenv
```

---

## Running the Stack

### Backend
```bash
# From: rosetta/
python rosetta-engine/server.py
# Runs FastAPI on http://0.0.0.0:8000
```

### Frontend
```bash
# From: rosetta/rosetta-workspace/
npm run dev
# Runs Next.js on http://localhost:3000
```

### Trigger a migration via curl
```bash
curl -X POST http://localhost:8000/api/migrate/stream \
  -H "Content-Type: application/json" \
  -d '{"file_path": "ofbiz-framework/applications/order/src/main/java/org/apache/ofbiz/order/shoppingcart/ShoppingCart.java", "target_method": "getGrandTotal"}'
```

---

## Pipeline Architecture

```
[User / CLI]
     |
     v
[FastAPI server.py]  POST /api/migrate/stream ? SSE stream
     |
     v
[LangGraph rosetta_pipeline]
     |
     +- 1. ast_context_node
     |       Parses ShoppingCart.java via javalang AST
     |       Records CALLS relationships into neo4j_context
     |
     +- 2. discovery_agent  (LLM: openai/gpt-oss-120b via Groq)
     |       Reads java_code + neo4j_context
     |       Outputs: logic_json, formula_ir, test_payload, test_cases
     |
     +- 3. architecture_agent  (LLM: openai/gpt-oss-120b via Groq)
     |       Reads logic_json + formula_ir
     |       Generates: calculate_getGrandTotal(request: dict) -> dict
     |       On retry: also reads validation_feedback from previous failure
     |
     +- 4. validator  (no LLM — pure Python)
     |       T1: Schema check — all required fields present in response?
     |       T3: Golden-file check — does output match 7 hand-authored fixtures?
     |       Shadow: Does output match Discovery-generated expected_output?
     |       On failure ? routes back to architecture_agent (max 3 retries)
     |
     +- 5. wrapper_node
             Wraps the pure function in a FastAPI router
```

---

## The Validator — In Detail

### T1 — Formula Completeness (core/formula_ir.py, core/validator.py:103-138)

Probes the generated function with an empty dict `{}` and checks that all 5 required fields are present in the response.

Required fields (from _manifest.json):
- sub_total
- total_shipping
- total_sales_tax
- order_other_adjustment_total
- order_global_adjustments

### T3 — Golden-File Equivalence (core/validator.py:140-218)

Runs 7 hand-authored fixtures through `calculate_getGrandTotal(fixture.input)`.
Comparison uses `core/equivalence.py:compare_outputs()` which normalises everything to Decimal(2dp) before diffing.

#### Input Schema (exact keys the function receives)
```json
{
  "cart_lines":         [{"item_sub_total": "120.00"}],
  "ship_info":          [{"ship_estimate": "10.00", "total_tax": "8.40"}],
  "adjustments":        [{"amount": "-10.00", "is_percent": false, "ship_group_seq_id": null}],
  "global_adjustments": [{"amount": "2.00", "is_percent": false, "ship_group_seq_id": null}]
}
```

#### Expected Output Schema (all values as 2dp strings)
```json
{
  "sub_total":                    "120.00",
  "total_shipping":               "10.00",
  "total_sales_tax":              "8.40",
  "order_other_adjustment_total": "-10.00",
  "order_global_adjustments":     "2.00",
  "grand_total":                  "130.40"
}
```

#### The 7 Golden Fixtures

| ID                              | Description                                         | grand_total |
|---------------------------------|-----------------------------------------------------|-------------|
| case_01_empty_cart              | No lines, no shipping                               | 0.00        |
| case_02_single_item             | One cart line, no shipping/tax/adj                  | 50.00       |
| case_03_multi_item_with_tax     | Multiple lines + tax                                | computed    |
| case_04_fixed_adjustment        | Negative fixed discount (-10.00) + global adj       | 130.40      |
| case_05_percentage_adjustment   | is_percent=true: (200.00 * -10.00) / 100 = -20.00  | 208.00      |
| case_06_global_adjustment_na    | Global adj, no ship_group                           | computed    |
| case_07_ship_group_excluded     | Adjustment excluded due to ship group               | computed    |

---

## Current Known Failures

### T3 — Golden-File Mismatch (PRIMARY BLOCKER)

The generated function handles simple cases correctly but fails on adjustment logic.

**Failure point 1 — Percentage adjustments (case_05)**
```json
{"amount": "-10.00", "is_percent": true, "ship_group_seq_id": null}
```
Expected: `(sub_total * amount) / 100 = (200.00 * -10.00) / 100 = -20.00`
LLM generates: uses amount directly as -10.00 (wrong)

**Failure point 2 — Adjustment vs Global routing**
`adjustments[]` ? feeds `order_other_adjustment_total`
`global_adjustments[]` ? feeds `order_global_adjustments`
LLM sometimes merges both arrays or misroutes based on ship_group_seq_id.

### T1 — Missing Response Fields (PARTIALLY FIXED)

Attempt 1 was returning only `{"grand_total": X}` instead of all 6 fields.
Fix applied in `core/agents.py:architecture_node` — prompt now contains the exact output schema.
Needs another test run to confirm.

### Shadow Tier — LLM Hallucination

Discovery Agent generates `expected_output` from LLM inference, not from actual Java execution.
It invents values like `{"grand_total": 137.10}` which don't match the real arithmetic.
This tier should be set to `baseline_mode = "golden_file"` to skip Shadow when golden fixtures exist.

---

## Correct Reference Implementation

If you want to verify that all 7 fixtures pass, use this function:

```python
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

QUANTUM = Decimal("0.01")

def _d(value) -> Decimal:
    try:
        return Decimal(str(value)).quantize(QUANTUM, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return Decimal("0.00")

def calculate_getGrandTotal(request: dict) -> dict:
    cart_lines         = request.get("cart_lines", [])
    ship_info          = request.get("ship_info", [])
    adjustments        = request.get("adjustments", [])
    global_adjustments = request.get("global_adjustments", [])

    sub_total       = sum(_d(l.get("item_sub_total", 0)) for l in cart_lines)
    total_shipping  = sum(_d(s.get("ship_estimate", 0)) for s in ship_info)
    total_sales_tax = sum(_d(s.get("total_tax", 0)) for s in ship_info)

    other_adj = Decimal("0.00")
    for adj in adjustments:
        amount = _d(adj.get("amount", 0))
        if adj.get("is_percent", False):
            other_adj += (sub_total * amount / Decimal("100")).quantize(QUANTUM, rounding=ROUND_HALF_UP)
        else:
            other_adj += amount

    global_adj  = sum(_d(a.get("amount", 0)) for a in global_adjustments)
    grand_total = sub_total + total_shipping + total_sales_tax + other_adj + global_adj

    def fmt(v): return str(v.quantize(QUANTUM, rounding=ROUND_HALF_UP))

    return {
        "sub_total":                    fmt(sub_total),
        "total_shipping":               fmt(total_shipping),
        "total_sales_tax":              fmt(total_sales_tax),
        "order_other_adjustment_total": fmt(other_adj),
        "order_global_adjustments":     fmt(global_adj),
        "grand_total":                  fmt(grand_total),
    }
```

---

## Suggested Next Steps

### Option A — Fix T3 via prompt (in progress)
Inject the is_percent algorithm as explicit pseudocode into the architecture agent prompt.
The fix is in core/agents.py:architecture_node. More specificity is needed.

### Option B — Fix T3 via golden_file baseline_mode
Set baseline_mode = "golden_file" in server.py initial state.
This skips the Shadow tier entirely and only runs T1 + T3.
Shadow was causing false positives because Discovery invents wrong expected_output values.

### Option C — Hardcode the reference implementation as fallback
If the LLM fails all 3 retries, use the reference implementation above as a deterministic fallback.
This guarantees T3 passes while the LLM improves.

### Priority 2 — Fix Shadow Tier permanently
Options:
- Run the golden oracle function on Discovery test_cases to derive correct expected_output
- OR set baseline_mode = "golden_file" globally when golden fixtures exist for the method

### Priority 3 — Extend to other ShoppingCart methods
Each new method needs:
- tests/baselines/<methodName>/_manifest.json
- tests/baselines/<methodName>/case_XX.json fixtures
- Hand-authored arithmetic_trace values

---

## Key Files Priority

| File                              | Purpose                                       | Read First? |
|-----------------------------------|-----------------------------------------------|-------------|
| core/agents.py                    | LLM prompt engineering (Discovery + Arch)     | YES         |
| core/validator.py                 | T1/T3/Shadow validation logic                 | YES         |
| tests/baselines/getGrandTotal/    | 7 golden fixtures + manifest                  | YES         |
| core/equivalence.py               | Decimal normalisation + diff                  | Yes         |
| core/formula_ir.py                | T1 schema extractor                           | Yes         |
| core/graph.py                     | LangGraph pipeline wiring                     | Yes         |
| server.py                         | FastAPI + SSE bridge                          | Reference   |
| parsers/ast_ingester.py           | Java AST parser                               | Reference   |

---

## Environment

```
GROQ_API_KEY=your_key    # in rosetta/.env
Model: openai/gpt-oss-120b via Groq
Framework: LangGraph + LangChain + FastAPI
DB: Neo4j embedded (in-memory, per migration_id)
```

---

*Built with LangGraph · LangChain · FastAPI · Next.js · Three.js · Neo4j*
