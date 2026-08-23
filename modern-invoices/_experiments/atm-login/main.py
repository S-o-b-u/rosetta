import os
import sys
import importlib
from pathlib import Path
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Rosetta Domain Service")

current_dir = Path(__file__).parent

# Auto-load engine for parity endpoint
engine_path = current_dir.parent / "rosetta-engine"
if str(engine_path) not in sys.path:
    sys.path.insert(0, str(engine_path))

# Auto-discover and mount all generated _service.py routers
for filename in os.listdir(current_dir):
    if filename.endswith("_service.py"):
        module_name = filename[:-3]
        try:
            spec = importlib.util.spec_from_file_location(module_name, current_dir / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "router"):
                app.include_router(module.router)
                print(f"[+] Mounted: {module_name}")
        except Exception as e:
            print(f"[!] Failed to load {filename}: {e}")

# Mount parity endpoint if available
try:
    from modern_invoices_parity import router as parity_router
    app.include_router(parity_router)
except Exception:
    try:
        import importlib.util, sys
        parity_path = current_dir / "parity_endpoint.py"
        if parity_path.exists():
            spec = importlib.util.spec_from_file_location("parity_endpoint", parity_path)
            parity_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(parity_mod)
            app.include_router(parity_mod.router)
            print("[+] Mounted: parity_endpoint")
    except Exception as e:
        print(f"[!] Parity endpoint not loaded: {e}")

@app.get("/health")
async def health_check():
    return {"status": "operational", "services": [
        f for f in os.listdir(current_dir) if f.endswith("_service.py")
    ]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
