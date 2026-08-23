"""
server.py — FastAPI SSE bridge for the Rosetta LangGraph pipeline.

Exposes the existing rosetta_pipeline via Server-Sent Events so the
Sandbox frontend can stream real migration progress without any mock data.
"""

import os
import sys
import json
import uuid
import re
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── Path setup ──
# Ensure rosetta-engine modules are importable
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if engine_path not in sys.path:
    sys.path.insert(0, engine_path)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import the REAL compiled LangGraph pipeline
from core.graph import rosetta_pipeline


# ── FastAPI App ──
app = FastAPI(title="Rosetta Pipeline Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Schema ──
class MigrateRequest(BaseModel):
    file_path: str
    target_method: str
    baseline_mode: str = "provisional"


# ── Helpers ──
def _sse_event(event: str, data: dict) -> str:
    """Format a single SSE event string."""
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _extract_java_method(java_code: str, method_name: str) -> str:
    """Extract a single method from a Java source file."""
    pattern = re.compile(
        rf"(public|protected|private|static|\s)+[\w\<\>\[\]]+\s+{method_name}\s*\("
    )
    match = pattern.search(java_code)
    if not match:
        return java_code

    start_idx = match.start()
    brace_start = java_code.find("{", start_idx)
    if brace_start == -1:
        return java_code

    brace_count = 0
    end_idx = -1
    for i in range(brace_start, len(java_code)):
        if java_code[i] == "{":
            brace_count += 1
        elif java_code[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break

    if end_idx != -1:
        return java_code[start_idx : end_idx + 1].strip()
    return java_code


def _safe_state_snapshot(state_update: dict) -> dict:
    """Create a JSON-serializable snapshot of the state update.
    Truncates very large string fields to keep SSE payloads manageable."""
    safe = {}
    for key, value in state_update.items():
        if isinstance(value, str) and len(value) > 5000:
            safe[key] = value[:5000] + f"...[truncated, total {len(value)} chars]"
        elif isinstance(value, dict):
            safe[key] = value
        elif isinstance(value, list):
            safe[key] = value
        elif isinstance(value, (bool, int, float, type(None))):
            safe[key] = value
        else:
            safe[key] = str(value)
    return safe


# ── Health Endpoint ──
@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── Migration Stream Endpoint ──
@app.post("/api/migrate/stream")
async def migrate_stream(request: MigrateRequest):
    """
    Starts a REAL Rosetta migration and streams pipeline events via SSE.
    Uses the existing rosetta_pipeline.stream() from LangGraph.
    """

    def event_generator():
        migration_id = f"mig-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        # ── Validate file ──
        if not os.path.exists(request.file_path):
            yield _sse_event("error", {
                "migration_id": migration_id,
                "error": f"File not found: {request.file_path}",
                "timestamp": now,
            })
            return

        # ── Read and extract Java method ──
        try:
            with open(request.file_path, "r", encoding="utf-8") as f:
                full_java_code = f.read()
            java_code = _extract_java_method(full_java_code, request.target_method)
        except Exception as e:
            yield _sse_event("error", {
                "migration_id": migration_id,
                "error": f"Failed to read file: {str(e)}",
                "timestamp": now,
            })
            return

        # ── Detect Golden Fixtures ──
        baseline_mode = request.baseline_mode
        manifest_path = os.path.join(engine_path, "tests", "baselines", request.target_method, "_manifest.json")
        if os.path.exists(manifest_path):
            baseline_mode = "golden_file"

        # ── Build the initial state (same shape as CLI) ──
        initial_state = {
            "migration_id": migration_id,
            "file_path": request.file_path,
            "target_method": request.target_method,
            "java_code": java_code,
            "test_payload": {},
            "expected_legacy_output": {},
            "formula_ir": None,
            "pure_function_source": None,
            "wrapped_service_source": None,
            "candidate_source": None,
            "test_cases": None,
            "baseline_mode": baseline_mode,
            "baseline_command": None,
            "validation_results": None,
            "parity_report": None,
            "retry_count": 0,
        }

        # ── Emit migration_started ──
        yield _sse_event("migration_started", {
            "migration_id": migration_id,
            "file_path": request.file_path,
            "target_method": request.target_method,
            "timestamp": now,
        })

        # ── Stream the REAL pipeline ──
        try:
            for chunk in rosetta_pipeline.stream(initial_state):
                ts = datetime.now(timezone.utc).isoformat()

                # LangGraph stream v1 yields dict of {node_name: state_update}
                for node_name, state_update in chunk.items():
                    safe_update = _safe_state_snapshot(state_update)

                    yield _sse_event("node", {
                        "migration_id": migration_id,
                        "node": node_name,
                        "timestamp": ts,
                        "state": safe_update,
                    })

                    # Check for terminal conditions in the state update
                    if state_update.get("validation_passed") is True:
                        yield _sse_event("migration_completed", {
                            "migration_id": migration_id,
                            "timestamp": ts,
                            "validation_passed": True,
                            "parity_report": state_update.get("parity_report"),
                        })

        except Exception as e:
            ts = datetime.now(timezone.utc).isoformat()
            yield _sse_event("error", {
                "migration_id": migration_id,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": ts,
            })
            return

        # ── Emit final done event ──
        yield _sse_event("stream_end", {
            "migration_id": migration_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Main entry point ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
