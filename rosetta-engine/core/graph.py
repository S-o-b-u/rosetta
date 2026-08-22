from langgraph.graph import StateGraph, END
from core.state import RosettaState
# Import the REAL LangChain agents we built!
from core.agents import discovery_node, architecture_node
from core.validator import validator_node
from core.wrapper import wrapper_node
from plugins.source.java_adapter import JavaSourceAdapter
from plugins.source.groovy_adapter import GroovySourceAdapter

SUPPORTED_SOURCE_LANGS = {
    "java": JavaSourceAdapter,
    "groovy": GroovySourceAdapter
}

def ast_context_node(state: RosettaState) -> RosettaState:
    migration_id = state.get("migration_id", "unknown-migration")
    file_path = state["file_path"]
    target_method = state["target_method"]
    source_lang = state.get("source_lang", "java")
    
    print(f"\n[Node] AST/Neo4j Context: Ingesting {target_method} via {source_lang} adapter...")
    
    AdapterClass = SUPPORTED_SOURCE_LANGS.get(source_lang.lower())
    if not AdapterClass:
        print(f"[!] MIGRATION FAILED — Unsupported source language: {source_lang}")
        return {"validation_passed": False, "validation_feedback": f"Unsupported source language: {source_lang}", "neo4j_context": None, "graph_context": "degraded"}
        
    try:
        adapter = AdapterClass()
        context = adapter.ingest_and_get_context(migration_id, file_path, target_method)
        return {"neo4j_context": context}
    except Exception as e:
        print(f"[!] MIGRATION FAILED — {source_lang} adapter failed: {e}")
        return {"validation_passed": False, "validation_feedback": f"{source_lang} adapter failed: {e}", "neo4j_context": None, "graph_context": "degraded"}


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