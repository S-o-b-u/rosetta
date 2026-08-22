# Project Rosetta — Current Project Status

**Team Asynchronous | InnoFusion 3.0 | Guru Nanak Institute of Technology**
Status as of: latest architecture documentation (`rosetta-workspace`)
Repo confirmed: `apache/ofbiz-framework` (active mainline, not the deprecated `apache/ofbiz` mirror)

---

## 1. Summary

The project has moved from pitch-deck concept to a documented technical architecture. The design has also **shifted meaningfully** from what was pitched — this doc captures both what's now specified and where it diverges from the original plan, so the team is working from one source of truth instead of two documents that quietly disagree.

**In one line:** Rosetta is now specified as a two-agent LangGraph pipeline (Discovery → Architecture) that ingests a legacy method, builds Neo4j dependency context via `javalang` AST parsing, and outputs an async FastAPI + SQLAlchemy microservice with OpenAPI spec — driven by a CLI and framework-agnostic JSON rule files.

---

## 2. What's Now Specified (from architecture doc)

### 2.1 Pipeline shape
A Directed Acyclic Graph orchestrated by **LangGraph**, backed by **Google Gemini** (`gemini-3.6-flash` via `langchain-google-genai`):

```
Legacy Monolith File
        │
        ▼
  AST Ingestion (javalang) ──► Neo4j Knowledge Graph (dependencies)
        │
        ▼
  Discovery Agent (LLM business-logic extraction)
        │
        ▼
  Intermediate JSON Schema (business_logic.json)
        │
        ▼
  Architecture Agent (Pydantic-enforced microservice generation)
        │
        ├──► Async FastAPI service + SQLAlchemy (asyncpg) models
        └──► OpenAPI v3 spec (YAML)
```

Flow is explicitly: `START → discover node → architect node → END`. Two nodes, not four.

### 2.2 Shared state contract
```python
class AgentState(TypedDict):
    target_method: str      # Target method/function identifier
    raw_java_code: str      # Raw source extracted from the target file
    neo4j_context: str      # Graph relationships and dependency context
    business_logic: str     # Extracted intermediate JSON business rules
    fastapi_code: str       # Generated async FastAPI Python implementation
    openapi_spec: str       # Generated OpenAPI v3 spec (YAML)
```

### 2.3 Discovery Agent
- Strips legacy boilerplate (`Delegator`, `GenericValue`, manual transaction dispatch) from raw source.
- Runs Gemini at zero-temperature for deterministic, structured extraction.
- Output IR includes: `service_name`, `trigger`, typed `inputs`, `database_interactions` (CRUD + affected tables + conditions), `business_rules_sequence`.

### 2.4 Architecture Agent
- Converts IR JSON into a `MicroserviceArtifacts` Pydantic model — enforces clean separation of generated code vs. generated docs.
- Outputs: async FastAPI endpoints (Pydantic models, camelCase/snake_case aliasing), SQLAlchemy async ORM (asyncpg), OpenAPI 3.0.3 YAML with request/response models and status codes (201/404/500).

### 2.5 Framework-agnostic rules engine
Parsing logic is decoupled into `rules/*.json` instead of hardcoded — currently defined for five frameworks:

| Rule file | Framework | Read pattern | Write/dispatch pattern |
|---|---|---|---|
| `ofbiz.json` | Apache OFBiz | `EntityQuery.from().where()` | `dispatcher.runSync()`, `runAsync()` |
| `spring_boot.json` | Spring Boot (Data JPA) | `@Query`, `findBy*` | `@Autowired` service calls |
| `java_ee.json` | Java EE / Jakarta (JPA) | `EntityManager.find()`, `createQuery()` | `@Inject`, `@EJB` |
| `django.json` | Django ORM | `.filter()`, `.get()` | Celery `@shared_task`, `.delay()` |
| `express_mongoose.json` | Express/Mongoose | `.find()`, `.findOne()`, `.findById()` | External HTTP (axios/fetch) |

### 2.6 CLI (`rosetta-cli/rosetta.py`)
```bash
# Initialize target repo, select framework rules, verify graph DB connection
python rosetta-cli/rosetta.py init --framework <ofbiz | spring_boot | java_ee | django | express_mongoose>

# Run ingestion + agent pipeline + artifact generation for one target method
python rosetta-cli/rosetta.py migrate --file <path> --target <method_name> --output <dir>
```
Each `migrate` run produces three files: `<target>_logic.json`, `<target>_service.py`, `<target>_openapi.yaml`.

### 2.7 Directory layout
```
rosetta-workspace/
├── .vscode/settings.json
├── dashboard/                  # React visual sandbox (UI status: not detailed in doc)
├── ofbiz-framework/             # Reference legacy monolith (confirmed correct repo)
├── rosetta-cli/rosetta.py
├── rosetta-engine/
│   ├── .venv/
│   ├── agents/
│   │   ├── discovery_agent.py
│   │   ├── architecture_agent.py
│   │   ├── orchestrator.py           # LangGraph StateGraph
│   │   ├── test_discovery_agent.py
│   │   └── test_architecture_agent.py
│   ├── core/                    # ingestion & graph mapping utilities
│   ├── parsers/                 # AST visitor/parser abstractions
│   └── rules/                   # *.json rule definitions (5 frameworks)
├── .env                          # GOOGLE_API_KEY, NEO4J_URI
└── docker-compose.yml            # local Neo4j container
```

### 2.8 Tech stack (as specified)
- **Orchestration:** `langgraph`, `langchain-core`
- **LLM:** Google Gemini (`gemini-3.6-flash`) via `langchain-google-genai` / `google-genai`
- **Validation/typing:** `pydantic` v2, `TypedDict`
- **AST parsing:** `javalang` (Java), Python `ast` (for the tool's own use, per stack list)
- **Graph DB:** `neo4j`
- **Target service stack:** `fastapi`, `uvicorn`, `sqlalchemy` (async), `asyncpg`
- **CLI:** `argparse`, `python-dotenv`

---

## 3. Where This Diverges From the Original Pitch — Needs a Team Decision

These aren't wrong, but they're **changes**, and right now they exist only in this doc, not reconciled with the pitch deck or hackathon implementation plan. Flagging before code diverges further:

| Area | Pitch deck said | This architecture doc says | Decision needed |
|---|---|---|---|
| **Agent count** | 4 agents: Discovery, Architecture, **Coding**, **Parity Testing** (with self-correct loop) | 2 nodes: Discovery → Architecture. Architecture Agent itself emits the FastAPI code — no separate Coding Agent | Confirm whether "Coding Agent" is just merged into Architecture Agent, or actually dropped |
| **Parity / verification** | Closed-loop parity testing (Locust replay + DB diff) was the **headline differentiator** — "not just code generation, but proof it's correct" | Not present anywhere in this architecture. Pipeline ends at `END` after code + spec generation, with no verification step | This is the biggest gap. Without it, the pitch's strongest claim ("vs. generic LLM tools, we verify correctness") is unsupported by the current design |
| **AST tooling** | JavaParser / tree-sitter / javalang (multiple options floated) | `javalang` only | Fine — javalang is a reasonable, simpler choice. Just confirm it's sufficient for the target method's complexity |
| **Framework scope** | OFBiz only, explicitly narrow-scoped for hackathon feasibility | Rules engine now supports 5 frameworks (OFBiz, Spring Boot, Java EE, Django, Express/Mongoose) | This is scope *expansion*, which cuts against the "narrow, demonstrable" hackathon strategy discussed earlier. Recommend: keep the rules engine as designed (it's genuinely good architecture — shows generality), but **only build and demo the `ofbiz.json` path**. Don't spend hackathon time validating the other four live. |
| **DB / ORM in generated service** | Not specified in detail | SQLAlchemy async + asyncpg | Fine, more production-realistic than the original FastAPI/Pydantic-only mention |
| **Groovy coverage** | Discussed as a stretch goal | Not mentioned in this doc — `javalang` only parses Java, not Groovy | Groovy stretch goal is currently unaddressed in the architecture; needs its own ingestion path if still in scope |
| **LLM provider** | "Hosted LLM API" (unspecified) | Google Gemini (`gemini-3.6-flash`) | Confirm API key/quota is provisioned and tested before demo day, not during |

**Recommendation:** Treat "parity testing" as the one gap that must be resolved before the hackathon, even as a minimal version (a single before/after response + DB-row diff for the target method is enough — it doesn't need Locust-scale load testing to make the point). Without it, Rosetta becomes "another AI code generator," which is exactly the category the pitch argues against.

---

## 4. Status by Component

| Component | Status |
|---|---|
| Target repo | ✅ Confirmed correct (`apache/ofbiz-framework`) |
| Target method scope | ✅ Locked in prior planning (`InvoiceServices.java` chain — `createInvoice` → `createInvoiceItem` → `updateInvoiceStatus`) |
| Discovery Agent design | ✅ Specified (extraction logic, IR schema) |
| Architecture Agent design | ✅ Specified (Pydantic-enforced output contract) |
| LangGraph orchestration | ✅ Specified (2-node DAG) |
| Rules engine | ✅ Specified for 5 frameworks; only `ofbiz.json` needed for demo |
| CLI spec | ✅ Specified (`init`, `migrate`) |
| Neo4j graph construction | ⚠️ Referenced as a step, but ingestion-to-graph logic not detailed in this doc — needs concrete implementation plan |
| Parity / verification layer | ❌ Missing from current architecture — see Section 3 |
| Groovy ingestion path | ❌ Not addressed |
| Dashboard (React sandbox) | ⚠️ Listed in directory layout only, no functional spec yet |
| Test harnesses | ⚠️ Files exist in layout (`test_discovery_agent.py`, `test_architecture_agent.py`) — content/coverage unknown |
| Docker / infra | ✅ `docker-compose.yml` for local Neo4j specified |

Legend: ✅ specified/decided · ⚠️ partially specified, needs work · ❌ not yet addressed

---

## 5. Immediate Next Steps

1. **Decide on the parity/verification gap** (Section 3) — this determines whether it's a 2-node or 3-node graph, and it's the pitch's core differentiator.
2. Flesh out the AST-ingestion → Neo4j graph-write logic — currently the least-specified part of an otherwise well-specified pipeline.
3. Confirm Gemini API access (key, quota, rate limits) works end-to-end before relying on it for a live demo.
4. Build and validate only the `ofbiz.json` rule path; leave the other four rule files as-is (they cost nothing to keep, and support the "framework-agnostic" claim in the pitch without needing to be demoed).
5. Decide Groovy's fate: drop it from scope explicitly, or add a second ingestion path (Groovy AST via `groovy.ast`) alongside `javalang` — don't leave it silently unaddressed.
6. Reconcile this document with the hackathon implementation plan (hour-by-hour schedule) so the team is building against one plan, not two.
