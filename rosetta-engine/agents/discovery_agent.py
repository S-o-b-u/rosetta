import os
import json
from typing import TypedDict, List, Dict
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. DEFINE THE STRICT OUTPUT SCHEMA (PYDANTIC)
# ==========================================
class DatabaseInteraction(BaseModel):
    table: str = Field(description="Name of the database table")
    action: str = Field(description="READ or WRITE")
    condition: str = Field(description="The condition or reason for this access")

class InputParameter(BaseModel):
    name: str = Field(description="Parameter name")
    type: str = Field(description="Data type (e.g., String, Object, GenericValue)")
    required: bool = Field(description="Is this parameter mandatory?")

class BusinessLogicPayload(BaseModel):
    service_name: str
    trigger: str = Field(description="What triggers this service?")
    inputs: List[InputParameter]
    database_interactions: List[DatabaseInteraction]
    business_rules_sequence: List[str] = Field(description="Step-by-step business rules extracted from code")

# ==========================================
# 2. DEFINE THE LANGGRAPH STATE
# ==========================================
class AgentState(TypedDict):
    target_method: str
    raw_java_code: str
    neo4j_context: str
    business_logic: str # Stores the final JSON payload

# ==========================================
# 3. NEO4J CONTEXT FETCHER TOOL
# ==========================================
def get_neo4j_context(method_name: str) -> str:
    """Queries Neo4j to get bounded context (tables and services) for the target method."""
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "rosetta_hackathon2026")
    
    query = """
    MATCH (s:Service {name: $name})-[r]->(target)
    RETURN type(r) AS relationship, target.name AS target_name, labels(target) AS target_type
    """
    
    context_lines = [f"Bounded Context for {method_name}:"]
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        with driver.session() as session:
            results = session.run(query, name=method_name)
            for record in results:
                rel = record["relationship"]
                tgt = record["target_name"]
                t_type = record["target_type"][0]
                context_lines.append(f"- {rel} {t_type}: {tgt}")
        driver.close()
    except Exception as e:
        return f"Error connecting to Neo4j: {e}"
        
    return "\n".join(context_lines)

# ==========================================
# 4. THE DISCOVERY AGENT NODE
# ==========================================
def run_discovery_agent(state: AgentState) -> AgentState:
    print(f"\n[Discovery Agent] Analyzing target: {state['target_method']}")
    
    # 1. Fetch Graph Context
    print("[Discovery Agent] Fetching dependencies from Neo4j...")
    neo4j_data = get_neo4j_context(state['target_method'])
    state['neo4j_context'] = neo4j_data
    
    # 2. Initialize LLM (Ensure GEMINI_API_KEY is in your environment variables)
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0) # Temp 0 for deterministic output
    
    # 3. Bind the Pydantic schema to force JSON output
    structured_llm = llm.with_structured_output(BusinessLogicPayload)
    
    # 4. Create the Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Enterprise Java Architect tasked with reverse-engineering legacy Apache OFBiz monoliths.
        Your goal is to extract pure business logic, input requirements, and database interactions from the provided code and dependency graph.
        Strip away all OFBiz-specific boilerplate (e.g., GenericDelegator, LocalDispatcher).
        Return ONLY valid JSON matching the requested schema."""),
        ("human", """
        TARGET METHOD: {target_method}
        
        GRAPH DEPENDENCIES (From Neo4j):
        {neo4j_context}
        
        RAW SOURCE CODE:
        {raw_java_code}
        """)
    ])
    
    # 5. Execute
    print("[Discovery Agent] Extracting business rules using LLM...")
    chain = prompt | structured_llm
    result = chain.invoke({
        "target_method": state["target_method"],
        "neo4j_context": state["neo4j_context"],
        "raw_java_code": state["raw_java_code"]
    })
    
    # 6. Store result in state
    state['business_logic'] = result.model_dump_json(indent=2)
    print("[Discovery Agent] Extraction complete!")
    
    return state