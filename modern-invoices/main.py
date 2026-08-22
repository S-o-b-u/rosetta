import os
import importlib
from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="Rosetta Domain Service",
    description="Dynamically loads all generated microservice routers in this directory.",
    version="1.0.0"
)

# ==========================================
# MAGIC ROUTER DISCOVERY
# ==========================================
# Get the absolute path of the directory where this main.py lives
current_dir = os.path.dirname(os.path.abspath(__file__))

print("\n--- Scanning for Rosetta Services ---")
for filename in os.listdir(current_dir):
    # Look for any Python file ending in '_service.py'
    if filename.endswith("_service.py"):
        module_name = filename[:-3]  # Strip the '.py' extension
        try:
            # Dynamically import the generated module
            module = importlib.import_module(module_name)
            
            # Check if the module has our generated APIRouter instance
            if hasattr(module, "router"):
                app.include_router(module.router)
                print(f"[+] Successfully mounted router from: {filename}")
            else:
                print(f"[-] Skipped {filename}: No 'router' instance found.")
                
        except Exception as e:
            print(f"[!] Failed to load {filename}: {e}")
print("-------------------------------------\n")


@app.get("/health")
async def health_check():
    """Basic health check endpoint for the API Gateway to ping."""
    return {"status": "operational", "domain": "dynamic-domain-service"}


if __name__ == "__main__":
    # Runs the central domain microservice on port 8001
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)