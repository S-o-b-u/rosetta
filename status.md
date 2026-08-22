# Project Rosetta — Current Project Status (v2)

**Team Asynchronous | InnoFusion 3.0 | Guru Nanak Institute of Technology**
Status as of: `PROJECT_ROSETTA_ARCHITECTURE.md` + first live `migrate` run (`getGrandTotal`)
Supersedes: `project-rosetta-status.md` (v1)

---

## 1. Summary

The critical gap flagged in v1 — no verification/parity layer — is now closed. The pipeline has grown from a 2-node DAG (Discovery → Architecture) into a validated, self-correcting loop with a real shadow-testing stage. The team has also run it live against actual OFBiz code (`ShoppingCart.getGrandTotal`), which surfaced real, specific bugs — captured in Section 4 below, since a first failed run with a real diff is more valuable than another round of design.

---

## 2. Current Architecture

### 2.1 Directory layout
```
rosetta-workspace/
├── rosetta-cli/
│   └── rosetta.py              # CLI controller: 'migrate' & 'plan'
├── rosetta-engine/
│   ├── core/
│   │   ├── agents.py           # Discovery & Architecture agents
│   │   ├── graph.py            # LangGraph StateGraph + shadow validation loop
│   │   └── state.py            # TypedDict state definitions
│   └── .venv/
└── dashboard/
    └── data/
        └── roadmap_graph.json  # Neo4j-compatible blueprint for React visualization
```

### 2.2 `rosetta plan` — bounded context mapping
```bash
python rosetta-cli/rosetta.py plan --dir ofbiz-framework/applications/order/src/main/java/org/apache/ofbiz/order
```
Walks the target directory, sends the file tree to Gemini Flash to group classes into bounded contexts (e.g. `ShoppingCartManagement`, `FinancialAccounting`, `ShippingAndFulfillment`), and emits a Neo4j-compatible JSON graph (domains + `BELONGS_TO` edges) to `dashboard/data/roadmap_graph.json` for visualization.

**Note:** this replaces the earlier per-method `javalang` AST → Neo4j dependency-graph approach described in v1. It's now a higher-level, LLM-driven domain-mapping step aimed at the dashboard, rather than fine-grained call/entity context feeding the Discovery Agent. See Section 3 for why this matters.

### 2.3 `rosetta migrate` — the agentic pipeline
```bash
python rosetta-cli/rosetta.py migrate --file ofbiz-framework/.../ShoppingCart.java --target getGrandTotal
```

- **Discovery Agent** (`discovery_node`): strips legacy boilerplate from the target Java method, extracts pure business logic, and synthesizes both a test payload and an expected legacy-output baseline.
- **Architecture Agent** (`architecture_node`): converts the extracted schema into a FastAPI `APIRouter` module with Pydantic validation and async route handlers.
- **Shadow Equivalence Validator**: writes the generated code to `./modern-invoices/{method}_service.py`, dynamically loads it via `importlib`, spins up an in-memory FastAPI `TestClient`, runs the synthesized payload against it, and diffs the result against the expected baseline. Prints a visual side-by-side diff.
- **Self-Healing Loop**: on mismatch, feeds the exact diff (e.g. `Expected: 137.1, Got: -2.5`) back into the Architecture Agent as a warning prompt. Capped at **3 retries**, then halts safely — confirmed working as intended (see Section 4).

### 2.4 Status table (updated)

| Component | Status |
|---|---|
| Target repo | ✅ Confirmed correct (`apache/ofbiz-framework`) |
| Discovery Agent | ✅ Implemented — see Section 4 for a real extraction-quality issue found in testing |
| Architecture Agent | ✅ Implemented — generates FastAPI + Pydantic router modules |
| Shadow equivalence testing | ✅ Implemented (in-memory `TestClient`, dynamic module loading) |
| Self-healing retry loop | ✅ Implemented and confirmed working (caps at 3, halts safely) |
| Comparison/diff logic in validator | ⚠️ Needs a fix — currently compares raw dicts without normalizing key case or value type (Section 4, Bug 1) |
| `plan` command / bounded-context mapping | ✅ Implemented, but see Section 3 — unclear if it still feeds `migrate`, or is now dashboard-only |
| Multi-framework rules engine (`ofbiz.json` etc., from v1 doc) | ❓ Not mentioned in the latest architecture doc — unclear if retained, dropped, or just omitted from this write-up |
| Groovy ingestion path | ❌ Still not addressed |
| Dashboard (React) | ⚠️ Consumes `roadmap_graph.json`; functional status not detailed |

---

## 3. Open Architecture Question — carried over and updated

**Does the Neo4j / bounded-context graph from `plan` actually feed the `migrate` pipeline, or is it a separate, dashboard-only artifact now?**

In the v1 doc, `neo4j_context` was a field in the shared agent state — the Discovery Agent was meant to use dependency-graph context during extraction. In this v2 doc, `plan` produces a *different kind* of graph (domain groupings for visualization) and it's not clear the `migrate` pipeline reads it at all. If Discovery Agent is now extracting from raw source alone, with no graph context, that's a meaningful simplification worth confirming deliberately — it may be exactly why the `getGrandTotal` extraction in Section 4 came back incomplete (no surrounding context on what `subTotal`/`totalShipping`/etc. actually represent or where they're set).

---

## 4. Live Debugging Findings — First Real `migrate` Run (`getGrandTotal`)

First real execution against `ShoppingCart.getGrandTotal` failed after 3 retries. The diff is informative — two distinct, independent bugs are visible:

```
Expected: {'subTotal': 120.0, 'totalShipping': 10.0, 'totalSalesTax': 8.4,
           'orderOtherAdjustmentTotal': -10.0, 'orderGlobalAdjustments': 2.0, 'grand_total': 130.4}
Got:      {'sub_total': '0.00', 'total_shipping': '0.00', 'total_sales_tax': '0.00',
           'order_other_adjustment_total': '-8.00', 'order_global_adjustments': '0.00', 'grand_total': '-8.00'}
```

### Bug 1 — Validator comparison is not normalized
Expected keys are `camelCase`, generated keys are `snake_case`. Expected values are floats, generated values are strings. A raw diff will report a mismatch here regardless of whether the underlying math is correct. **This must be fixed before the retry signal can be trusted** — right now the self-healing loop may be reacting to formatting noise as much as (or instead of) real logic errors.

**Fix:** in the shadow validator, normalize both dicts (lower/snake-case all keys, coerce all values to float) before diffing.

### Bug 2 — Real logic error, once formatting noise is set aside
`order_other_adjustment_total` (-8.00) and `grand_total` (-8.00) are identical in the generated output. This strongly suggests the generated implementation returns the adjustment field directly rather than summing `subTotal + totalShipping + totalSalesTax + orderOtherAdjustmentTotal + orderGlobalAdjustments`. All other components came back `0.00` — either not read from the payload, or dropped from the formula entirely. The adjustment value itself is also wrong (-8 vs. expected -10), pointing to the **Discovery Agent's extraction**, not just the Architecture Agent's code generation, as the likely root cause.

**Fix, in order:**
1. Normalize the validator (Bug 1) first, so future diffs are trustworthy.
2. Manually inspect the real `getGrandTotal` source in `ShoppingCart.java` and compare it against what `discovery_node` wrote to `getGrandTotal_logic.json` — confirm whether the extraction actually captured all five terms of the formula.
3. If extraction is incomplete, this ties back to Section 3 — the agent may need more surrounding context (field definitions, related methods) than a single isolated method body provides.
4. If extraction is correct but generation drops terms, strengthen the Architecture Agent's prompt to explicitly require using every field present in `business_logic`, not a subset.

---

## 5. Immediate Next Steps

1. Fix the shadow validator's normalization (Bug 1) — quick, unblocks trustworthy signal for everything else.
2. Debug the `getGrandTotal` extraction/generation gap (Bug 2) using the source-vs-IR comparison above.
3. Resolve the open question in Section 3 — decide explicitly whether `plan`'s graph output should feed `migrate`, and document that decision so it doesn't drift again.
4. Confirm whether the multi-framework rules engine from v1 is still part of the design; if dropped, that's fine, but say so explicitly rather than letting it silently disappear between doc versions.
5. Once one method migrates cleanly end-to-end, treat `getGrandTotal` as the reference "known-good" demo path and lock it — don't keep testing new methods against an unfixed validator.