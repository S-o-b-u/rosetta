# Rosetta Equivalence Testing - Implementation Plan

**Status:** Proposed implementation plan  
**Scope:** Resolve the `getGrandTotal` equivalence-testing failure and establish a trustworthy parity workflow  
**Primary references:** [status.md](status.md), [project-rosetta-implementation.md](project-rosetta-implementation.md), [ShoppingCart.java](ofbiz-framework/applications/order/src/main/java/org/apache/ofbiz/order/shoppingcart/ShoppingCart.java)

## 1. Problem Statement

The current shadow validator cannot reliably distinguish a real business-logic mismatch from a representation mismatch.

The live failure showed:

```text
Expected: {'subTotal': 120.0, 'totalShipping': 10.0, 'totalSalesTax': 8.4,
           'orderOtherAdjustmentTotal': -10.0, 'orderGlobalAdjustments': 2.0,
           'grand_total': 130.4}
Got:      {'sub_total': '0.00', 'total_shipping': '0.00', 'total_sales_tax': '0.00',
           'order_other_adjustment_total': '-8.00',
           'order_global_adjustments': '0.00', 'grand_total': '-8.00'}
```

There are four related issues:

1. **Comparison noise:** expected keys are camelCase and generated keys are snake_case; expected numbers are floats and generated `Decimal` values are serialized as strings.
2. **Candidate lifecycle bug:** the validator loads `./modern-invoices/<target>_service.py` from disk, but the active CLI writes generated source only after the pipeline succeeds. A fresh migration therefore cannot validate its own candidate reliably.
3. **Extraction/fixture weakness:** the active Discovery prompt receives raw source only and synthesizes both the input payload and the expected baseline. The generated fixture can omit the state needed to exercise `getSubTotal`, shipping, tax, and both adjustment methods.
4. **Generation contract weakness:** the Architecture prompt says to calculate list fields, but does not require every formula term and does not define a canonical response naming/number representation.

The Java source confirms that `getGrandTotal()` is explicitly:

```text
getSubTotal()
+ getTotalShipping()
+ getTotalSalesTax()
+ getOrderOtherAdjustmentTotal()
+ getOrderGlobalAdjustments()
```

The helper methods immediately below it define the adjustment semantics. This surrounding context must be available to Discovery for a meaningful migration fixture.

## 2. Desired End State

A migration candidate should be validated in memory or in an isolated temporary workspace before it is accepted. Validation should:

- execute the exact generated candidate returned by Architecture;
- invoke an explicit endpoint, not the first route found in a router;
- normalize only transport representation differences;
- compare the normalized response against a separately defined baseline;
- produce a structured diff identifying missing fields, extra fields, type differences, and numeric differences;
- feed actionable logic feedback into a bounded retry loop;
- write artifacts only after validation passes;
- preserve the original raw response and normalized response for auditability.

For the reference `getGrandTotal` flow, a valid result must contain all five formula components and produce the expected grand total from a fixture that exercises non-zero lines, shipping, tax, and adjustments.

## 3. Implementation Strategy

### Phase 0 - Freeze the failure as a regression fixture

**Goal:** Make the current problem reproducible without another live Gemini call.

Tasks:

1. Add a small deterministic generated router fixture representing the observed bad output.
2. Add a deterministic expected response using the live-run values.
3. Add a valid `getGrandTotal` fixture with non-zero values for all five formula terms.
4. Store fixtures under a focused test area, for example `rosetta-engine/tests/fixtures/`.
5. Ensure tests can import `core.graph` or the validator helper without requiring a Gemini API key.

Acceptance criteria:

- A test fails before the validator fix because camelCase/float values do not match snake_case/string values.
- A test demonstrates that normalization removes representation-only differences.
- A test still fails when the grand-total math is genuinely wrong.

### Phase 1 - Extract validator utilities

**Goal:** Separate loading, invocation, normalization, and comparison so each behavior can be tested independently.

Suggested module:

```text
rosetta-engine/core/equivalence.py
```

Suggested functions:

```python
def load_router_from_source(source: str, module_name: str) -> ModuleType:
    """Compile candidate Python source in an isolated temporary module."""

def invoke_candidate(
    module: ModuleType,
    payload: dict[str, Any],
    route_path: str,
    method: str = "POST",
) -> dict[str, Any]:
    """Invoke the declared candidate endpoint with TestClient."""

def normalize_json(value: Any) -> Any:
    """Normalize key naming and numeric representations recursively."""

def compare_outputs(expected: Any, actual: Any) -> EquivalenceResult:
    """Return pass/fail plus structured field-level differences."""
```

`EquivalenceResult` should include:

- `passed: bool`;
- `expected_normalized`;
- `actual_normalized`;
- `differences`, with paths such as `$.grand_total`;
- a human-readable feedback string for Architecture.

Do not normalize blindly by converting every string to a float. Convert only numeric strings that are valid finite numbers, and preserve ordinary text. Use a decimal-aware representation internally to avoid introducing binary floating-point error.

### Phase 2 - Define canonical response normalization

**Goal:** Fix Bug 1 without hiding Bug 2.

Normalization rules:

1. Recursively process dictionaries and lists.
2. Convert keys to one canonical form, preferably snake_case.
3. Support common Java/Python naming boundaries, including:
   - `subTotal` -> `sub_total`;
   - `totalShipping` -> `total_shipping`;
   - `orderOtherAdjustmentTotal` -> `order_other_adjustment_total`;
   - `grand_total` remains `grand_total`.
4. Convert `int`, `float`, `Decimal`, and numeric strings to a decimal-aware comparable value.
5. Apply a documented monetary tolerance, preferably exact cents after quantization rather than an arbitrary float tolerance.
6. Preserve booleans, nulls, and non-numeric strings.
7. Compare required keys explicitly so missing values do not become silent defaults.

For money values, compare quantized values at the contract scale, for example:

```text
Decimal("130.4") -> Decimal("130.40")
Decimal("130.40") -> Decimal("130.40")
```

Do not treat `0.00` and a missing field as equivalent.

Acceptance criteria:

- CamelCase keys and snake_case keys compare equal after normalization.
- Float, integer, `Decimal`, and numeric-string monetary representations compare equal at cents precision.
- `130.40` does not compare equal to `130.41`.
- Missing or extra business fields remain failures.
- A wrong `grand_total` remains a failure after normalization.

### Phase 3 - Validate the in-memory candidate, not a stale file

**Goal:** Fix the artifact lifecycle bug.

Change the active state in [state.py](rosetta-engine/core/state.py) to carry the candidate execution metadata:

```text
candidate_source: str
candidate_route: str
candidate_method: str
```

Architecture should return `candidate_source` in state. The validator should:

1. read `state["generated_python"]` directly, or use the renamed `candidate_source` consistently;
2. compile it into a unique temporary module with `importlib`; 
3. inspect declared routes and select the route recorded in state or returned by Architecture;
4. run the request through an in-memory FastAPI `TestClient`;
5. delete temporary resources after execution.

The CLI should write `<target>_service.py` only after validation passes. On failure, it may optionally write a clearly named candidate/debug file, but it must never present that file as certified output.

If a file-based load remains necessary for demonstration, write the candidate to a temporary directory supplied in state, never to a fixed `./modern-invoices` path.

Acceptance criteria:

- A migration with a new target and a non-default `--output` validates the current generated candidate.
- Validation does not read stale `modern-invoices` artifacts.
- No generated service artifact is marked successful before validation passes.
- Import failures and missing routers produce structured validator failures.

### Phase 4 - Make endpoint selection explicit

**Goal:** Remove route-selection ambiguity.

Replace the current "first route in `module.router.routes`" behavior with one of these contracts:

1. Architecture returns `candidate_route` and `candidate_method`; or
2. the target method maps to a deterministic endpoint contract in the state.

For the reference path, use:

```text
method: POST
path: /calculate-grand-total
```

The validator should reject a candidate that does not expose the expected method/path instead of silently trying `GET` after a failed `POST`. A fallback may be retained only as a diagnostic mode.

Acceptance criteria:

- A router with multiple endpoints invokes the intended endpoint.
- A wrong path or HTTP method fails with a clear contract error.
- The validator feedback identifies the expected and available routes.

### Phase 5 - Strengthen Discovery with method context and a test contract

**Goal:** Fix the likely root cause of the zero components and incorrect adjustment.

The active Discovery node currently receives the whole Java file, but its prompt does not require surrounding helper methods or a structured formula contract. Update Discovery to produce a versioned intermediate representation with:

```json
{
  "method_name": "getGrandTotal",
  "formula_terms": [
    {"name": "sub_total", "source_method": "getSubTotal", "required": true},
    {"name": "total_shipping", "source_method": "getTotalShipping", "required": true},
    {"name": "total_sales_tax", "source_method": "getTotalSalesTax", "required": true},
    {"name": "order_other_adjustment_total", "source_method": "getOrderOtherAdjustmentTotal", "required": true},
    {"name": "order_global_adjustments", "source_method": "getOrderGlobalAdjustments", "required": true}
  ],
  "formula": "sub_total + total_shipping + total_sales_tax + order_other_adjustment_total + order_global_adjustments",
  "test_payload": {},
  "expected_output": {}
}
```

For `getGrandTotal`, provide the method body plus the directly referenced helper method bodies and relevant field declarations. At minimum, include:

- `getSubTotal`;
- `getTotalShipping`;
- `getTotalSalesTax`;
- `getOrderOtherAdjustmentTotal`;
- `getOrderGlobalAdjustments`;
- adjustment calculation semantics from `OrderReadHelper.calcOrderAdjustments` if available.

The Discovery prompt must require:

- every formula term to appear in `expected_output`;
- a payload that gives every term a non-zero or intentionally zero test value;
- an explanation of how each payload section maps to a Java field or helper;
- no invented expected values that cannot be traced to the fixture and formula.

Important: an LLM-generated expected output is still only a provisional oracle. It should be labeled as such until it is compared with an independently executed Java baseline.

Acceptance criteria:

- The generated IR contains all five `getGrandTotal` terms.
- The fixture includes cart lines, ship groups, tax, other adjustments, and global adjustments.
- The expected grand total equals the sum of the five expected components.
- A schema/consistency check rejects an expected output that omits a required formula term.

### Phase 6 - Strengthen Architecture generation

**Goal:** Prevent the generator from dropping terms after Discovery succeeds.

Update the Architecture prompt and add a pre-validation static contract check:

1. Require every `formula_terms[].name` to be represented in the response model.
2. Require the final expression to include every required term exactly once.
3. Require aliases for the canonical API contract where needed, for example camelCase input compatibility with snake_case Python fields.
4. Require monetary values to use `Decimal` and a declared serialization policy.
5. Require the returned endpoint path and method to be included in state.
6. Reject generated code that returns a component field as `grand_total` without combining all required terms.

The static check should not try to prove arbitrary Python semantics. It should catch obvious omissions and leave numerical proof to the runtime validator.

Acceptance criteria:

- A generated implementation that omits `total_shipping` is rejected before shadow execution or fails with a precise contract message.
- The `getGrandTotal` router accepts the chosen fixture shape.
- The response has the declared canonical fields and types.

### Phase 7 - Establish an independent baseline

**Goal:** Make the word "equivalence" technically defensible.

The current expected response is synthesized by Discovery, which means the same model helps define both the implementation requirements and the oracle. Replace or supplement it with a baseline provider:

```text
BaselineProvider
  -> invoke legacy Java method with fixture
  -> capture serialized response
  -> return response + metadata
```

For the first reference demo, use a deterministic baseline fixture if running OFBiz is too expensive. Record:

- fixture identifier;
- source commit/version;
- Java method and helper methods used;
- expected component values;
- rounding and scale policy;
- capture timestamp;
- whether the baseline was executed or manually approved.

Later, connect the provider to a running OFBiz test endpoint or a dedicated Java harness. Database-row diffing should be added only after response-level parity is stable.

Acceptance criteria:

- The validator can distinguish `llm_synthesized`, `manual_fixture`, and `java_executed` baselines.
- A generated service cannot certify itself solely against a model-invented expected value in production mode.
- The demo clearly labels provisional versus independently executed parity.

### Phase 8 - Lock the reference path with tests

**Goal:** Prevent regressions while broader features remain unsettled.

Add deterministic tests for:

1. `normalize_json` key conversion and numeric conversion.
2. Monetary cents precision and mismatch tolerance.
3. Missing/extra field detection.
4. Candidate source loading without disk artifacts.
5. Explicit route/method selection.
6. HTTP error handling.
7. Validator feedback formatting.
8. Retry routing at zero, one, two, and three retries.
9. Full `getGrandTotal` arithmetic with:
   - empty cart;
   - one line item;
   - multiple line items;
   - shipping and tax;
   - fixed negative adjustment;
   - percentage adjustment;
   - global adjustment with no ship group;
   - ship-group adjustment excluded from global adjustments;
   - negative and rounding edge cases.
10. CLI writes artifacts only after validation success.

Use mocked LLM responses for agent tests. Keep live Gemini and Neo4j checks as explicitly marked integration tests.

## 4. Recommended Execution Order

```text
1. Freeze failing and passing fixtures
2. Extract normalization/comparison utilities
3. Fix candidate loading and output-directory coupling
4. Make route selection explicit
5. Run focused validator tests
6. Strengthen Discovery IR and context window
7. Strengthen Architecture contract
8. Re-run getGrandTotal reference migration
9. Add independent Java baseline mode
10. Reconnect plan/Neo4j context after parity is stable
```

The first four steps should be completed before changing prompts. Otherwise the retry loop will continue to generate feedback that mixes formatting errors, stale-file errors, and actual business-logic errors.

## 5. Definition Of Done

The equivalence issue is resolved when all of the following are true:

- `getGrandTotal` validates using the current in-memory generated candidate.
- The validator normalizes camelCase/snake_case and numeric transport forms without masking missing fields or incorrect money values.
- The fixture exercises all five formula terms.
- The IR explicitly lists all five terms and their source methods.
- The generated `grand_total` is computed from all required terms.
- A real wrong total still fails after normalization.
- The retry feedback identifies the failing field and expected arithmetic.
- A non-default output directory works.
- Certified artifacts are written only after a pass.
- Deterministic tests cover the validator and reference service.
- The report identifies whether the baseline is LLM-synthesized, manually approved, or Java-executed.

## 6. Design Decisions To Record

Before implementation begins, record these decisions in `status.md` or a project decision log:

1. **Canonical API naming:** snake_case internally with camelCase aliases, or camelCase throughout the external contract.
2. **Money comparison policy:** exact cents after quantization versus a documented decimal tolerance.
3. **Baseline authority:** provisional LLM fixture versus independently executed Java response.
4. **Graph role:** dashboard-only `plan` output versus context supplied to Discovery.
5. **Pipeline ownership:** active `rosetta-engine/core` implementation versus the older `rosetta-engine/agents` implementation.
6. **Artifact policy:** whether failed candidates are retained for debugging and where they are stored.

## 7. Short-Term Deliverables

| Deliverable | Owner surface | Completion signal |
|---|---|---|
| Normalization utility | `rosetta-engine/core/equivalence.py` | Representation-only mismatch passes |
| In-memory candidate execution | `rosetta-engine/core/graph.py` | No fixed-path dependency |
| Explicit route contract | `rosetta-engine/core/state.py`, `core/agents.py` | Intended endpoint is invoked |
| Reference fixtures | `rosetta-engine/tests/fixtures/` | Deterministic failing/passing cases |
| Discovery formula IR | `rosetta-engine/core/agents.py` | Five `getGrandTotal` terms present |
| Architecture contract check | `rosetta-engine/core/graph.py` or `core/equivalence.py` | Missing formula terms rejected |
| Independent baseline metadata | State or artifact manifest | Oracle provenance visible |
| Regression suite | `rosetta-engine/tests/` | Reference path remains green |

## 8. Final Recommendation

Treat normalization and candidate execution as correctness infrastructure, not prompt tuning. Fix those first, then use the resulting trustworthy field-level diff to repair Discovery and Architecture. The `getGrandTotal` method should become the locked reference migration only after it passes with a fixture that exercises every term and a baseline whose provenance is explicit.
