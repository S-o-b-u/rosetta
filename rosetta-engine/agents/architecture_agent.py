import json
from typing import TypedDict
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. EXPAND THE LANGGRAPH STATE
# ==========================================
class AgentState(TypedDict):
    target_method: str
    raw_java_code: str
    neo4j_context: str
    business_logic: str
    fastapi_code: str  # Generated Python code
    openapi_spec: str  # Generated YAML spec

# ==========================================
# 2. DEFINE THE OUTPUT SCHEMA (PYDANTIC)
# ==========================================
class MicroserviceArtifacts(BaseModel):
    fastapi_code: str = Field(description="Production-ready FastAPI Python code implementing the business logic using SQLAlchemy and asyncpg.")
    openapi_spec: str = Field(description="OpenAPI v3 specification in YAML format for the generated endpoint.")

# ==========================================
# 3. THE ARCHITECTURE AGENT NODE
# ==========================================
def run_architecture_agent(state: AgentState) -> AgentState:
    print(f"\n[Architecture Agent] Architecting modern microservice for: {state['target_method']}")
    
    # Ensure we have the business logic from the Discovery Agent
    if not state.get("business_logic"):
        raise ValueError("Missing business_logic in state. Discovery Agent must run first.")
    
    # Initialize Gemini (Using the stable 3.6-flash model)
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    
    # Bind the Pydantic schema to force structured output
    structured_llm = llm.with_structured_output(MicroserviceArtifacts)
    
    # Create the Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an elite Backend Technical Architect specializing in scalable distributed systems.
        Your task is to transform a JSON payload containing extracted legacy business rules into a modern microservice component.
        
        CRITICAL ARCHITECTURE CONSTRAINTS:
        1. Do NOT create a standalone `app = FastAPI()` instance.
        2. You MUST use `APIRouter()` from fastapi. 
        3. Initialize the router exactly like this: `router = APIRouter(tags=["Generated Service"])`
        4. Attach your endpoints to this `router` (e.g., `@router.post("/api/v1/...")`).
        5. Include all required asynchronous SQLAlchemy models (`asyncpg`) and Pydantic schemas in the same file.
        6. Do NOT include `uvicorn.run()` or an `if __name__ == "__main__":` block.
        7. Generate a complete, valid OpenAPI v3 YAML specification for the service.
        
        Focus on performance, clean architecture, and exact parity with the provided business rules.
        Return the exact Python code and YAML string."""),
        ("human", """
        EXTRACTED BUSINESS LOGIC (JSON):
        {business_logic}
        """)
    ])
    
    # Execute
    print("[Architecture Agent] Generating FastAPI code and OpenAPI spec using Gemini...")
    chain = prompt | structured_llm
    
    result = chain.invoke({
        "business_logic": state["business_logic"]
    })
    
    # Store results in state
    state['fastapi_code'] = result.fastapi_code
    state['openapi_spec'] = result.openapi_spec
    print("[Architecture Agent] Microservice artifacts generated successfully!")
    
    return state