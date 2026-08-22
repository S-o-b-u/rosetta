# Rosetta Pipeline Context & State

## 1. Project Overview
**Rosetta** is an Agentic Legacy-to-Cloud-Native Migration Engine. Its primary goal is to convert monolithic Java business logic (specifically from Apache OFBiz, e.g., `ShoppingCart.java`) into modern, mathematically proven, pure Python FastAPI microservices. 

The system uses a Multi-Agent architecture driven by LangGraph, operating on the Groq API (using the free-tier `openai/gpt-oss-120b` model).

## 2. Pipeline Architecture
The migration pipeline executes in four sequential nodes:
1. **Discovery Agent (`core/agents.py`)**: Slices out the target method from the Java file, analyzes the abstract business logic, and generates a structured JSON schema detailing formula components and sample payloads.
2. **Architecture Agent (`core/agents.py`)**: A pure LLM-driven node that takes the Discovery schema and generates a framework-agnostic, pure Python function (`_function.py`) to execute the math.
3. **Validator (`core/validator.py`)**: A robust Multi-Tier Equivalence Testing engine.
   - **T1 (Formula Completeness)**: Ensures all required schema fields are returned.
   - **T3 (Golden File)**: Runs the generated Python function against hand-authored legacy data fixtures to prove 100% mathematical parity.
   - **Shadow**: Validates against LLM-hallucinated test cases (used as a fallback when Golden Files aren't available).
   - *TDD Loop*: If validation fails, the exact payload, expected trace, and mismatch differences (or Python exceptions) are fed back into the Architecture Agent for autonomous self-healing.
4. **Wrapper (`core/wrapper.py`)**: Takes the certified pure Python function and wraps it deterministically in a FastAPI `@router.post` endpoint (`_service.py`).
5. **API Gateway (`modern-invoices/main.py`)**: Automatically scans the directory and mounts all generated `_service.py` routers onto a live Uvicorn web server.

## 3. Major Architectural Fixes Applied
We recently resolved several critical roadblocks to stabilize the pipeline for 100% autonomous operation:

### A. Token Flooding & Context Limits (`rosetta.py`)
- **Problem**: The pipeline was feeding the entire 10,000-line, 56,000-token `ShoppingCart.java` monolith into the prompt, crashing the Groq `gpt-oss-120b` API with `413 Request too large` errors due to an 8,000 TPM limit.
- **Fix**: Implemented `extract_java_method()` in the CLI using regex signature matching and AST brace-counting. It now slices out *only* the specific target method string (e.g., 20 lines) and discards the rest of the monolith before hitting the LLM.

### B. LLM JSON Parsing Resiliency (`core/agents.py`)
- **Problem**: The open-weights model occasionally forgot trailing commas or malformed the Discovery JSON payload, crashing the pipeline.
- **Fix**: Wrapped the LangChain invocation in a 3-attempt `try/except json.JSONDecodeError` retry loop, allowing the agent to self-heal formatting mistakes.

### C. Unblocking the TDD Feedback Loop (`core/validator.py`)
- **Problem**: When the generated Python code threw runtime exceptions (e.g., `KeyError` on unexpected payload structures), the Validator masked the exception and returned empty `{}` diffs to the Architecture Agent, completely blinding the TDD loop.
- **Fix**: Modified `validator.py` to catch `Exception` during fixture execution and explicitly format the Python stack trace into the `validation_feedback`. The Architecture Agent now successfully reverse-engineers legacy data structures purely from Golden File exception feedback!

### D. Eliminating Shadow Testing False Positives (`core/validator.py`)
- **Problem**: The Discovery Agent lacks the context of the full file, so it hallucinates inaccurate payload keys for its test cases. This caused the Shadow Testing tier to fail perfect code when running against Golden Files.
- **Fix**: Added a bypass in `validator.py` so that if `--baseline-mode golden_file` is specified, the Shadow testing loop is completely skipped.

### E. FastAPI Signature Alignment (`core/wrapper.py`)
- **Problem**: The deterministic FastAPI template wrapped payloads inside a strict Pydantic model (`{"payload": {...}}`), which broke compatibility with the raw OFBiz JSON structures the pure functions expected.
- **Fix**: Refactored the `wrapper.py` template to accept `payload: Dict[str, Any]` directly, ensuring the API behaves identically to the legacy Java endpoints.

## 4. Current State
- The pipeline is fully operational, stable, and completely automated.
- It relies entirely on the TDD loop to infer business logic rather than hardcoded prompt rules.
- Services like `getGrandTotal` (using Golden Files) and `getTotalDiscountAmount` (using Provisional/Shadow testing) successfully migrate and mount to the `modern-invoices/` microservice gateway on port 8001.
