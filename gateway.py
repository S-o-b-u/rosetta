from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(title="Rosetta API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODERN_MICROSERVICE_URL = "http://localhost:8001"

# 1. LEGACY CATCH-ALL (Must come first!)
@app.api_route("/api/v1/legacy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_to_legacy_monolith(path: str, request: Request):
    """Routes explicitly unmigrated endpoints to the Java Monolith."""
    print(f"[Gateway] Routing /api/v1/legacy/{path} -> Legacy Java Monolith")
    
    mock_java_response = {
        "status": "SUCCESS",
        "message": "Processed by Legacy Java Monolith",
        "data": {"tracking": f"TRK-{path.upper()}-99281"}
    }
    headers = {"X-Powered-By": "Servlet/3.1 JSP/2.3 (Tomcat)"}
    return JSONResponse(status_code=200, content=mock_java_response, headers=headers)


# 2. MODERN CATCH-ALL (Must come second!)
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_to_modern_service(path: str, request: Request):
    """Intercepts all other /api/v1/ traffic and proxies it to the new Python microservices."""
    print(f"[Gateway] Routing /api/v1/{path} -> Modern Python Service (Port 8001)")
    
    async with httpx.AsyncClient(base_url=MODERN_MICROSERVICE_URL) as client:
        try:
            body = await request.body()
            response = await client.request(
                method=request.method,
                url=f"/api/v1/{path}",
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                content=body,
                params=request.query_params
            )
            return JSONResponse(status_code=response.status_code, content=response.json())
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Modern Service Unreachable: {exc}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway:app", host="0.0.0.0", port=8000, reload=True)