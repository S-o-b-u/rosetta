from langgraph.graph import StateGraph, END
from core.state import RosettaState
# Import the REAL LangChain agents we built!
from core.agents import discovery_node, architecture_node
from core.validator import validator_node
from core.wrapper import wrapper_node
from parsers.ast_ingester import ingest_and_get_context

def ast_context_node(state: RosettaState) -> RosettaState:
    migration_id = state.get("migration_id", "unknown-migration")
    file_path = state["file_path"]
    target_method = state["target_method"]
    
    print(f"\n[Node] AST/Neo4j Context: Ingesting {target_method}...")
    try:
        context = ingest_and_get_context(migration_id, file_path, target_method)
        return {"neo4j_context": context}
    except Exception as e:
        print(f"[!] AST Ingestion failed: {e}")
        return {"neo4j_context": None}


# ==========================================
# ROUTING LOGIC
# ==========================================
def route_validation(state: RosettaState) -> str:
    if state.get("validation_passed", False):
        return "wrapper"
    
    if state.get("retry_count", 0) >= 3:
        print("[!] Max retries reached. Halting pipeline.")
        return END
        
    return "architecture_agent"

# ==========================================
# 3. GRAPH ASSEMBLY
# ==========================================
workflow = StateGraph(RosettaState)

# Add the nodes (using the imported functions from agents.py and wrappers)
workflow.add_node("ast_context_node", ast_context_node)
workflow.add_node("discovery_agent", discovery_node)
workflow.add_node("architecture_agent", architecture_node)
workflow.add_node("validator", validator_node)
workflow.add_node("wrapper", wrapper_node)

# Set the flow
workflow.set_entry_point("ast_context_node")
workflow.add_edge("ast_context_node", "discovery_agent")
workflow.add_edge("discovery_agent", "architecture_agent")
workflow.add_edge("architecture_agent", "validator")

# Add the autonomous healing loop
workflow.add_conditional_edges(
    "validator",
    route_validation,
    {
        END: END,
        "wrapper": "wrapper",
        "architecture_agent": "architecture_agent"
    }
)
workflow.add_edge("wrapper", END)

rosetta_pipeline = workflow.compile()