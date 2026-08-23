import os
# pyrefly: ignore [missing-import]
from neo4j import GraphDatabase
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from core.state import RosettaState
# Import the REAL LangChain agents we built!
from core.agents import discovery_node, architecture_node
from core.validator import validator_node
from core.wrapper import wrapper_node
from plugins.source.java_adapter import JavaSourceAdapter
from plugins.source.groovy_adapter import GroovySourceAdapter

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

SUPPORTED_SOURCE_LANGS = {
    "java": JavaSourceAdapter,
    "groovy": GroovySourceAdapter
}


# ==========================================
# 0. NEO4J HEALTH GATE (First node in graph)
# ==========================================
def neo4j_health_check_node(state: RosettaState) -> RosettaState:
    """
    Pings Neo4j before any analysis begins. If the DB is unreachable,
    the pipeline short-circuits immediately with a clear diagnostic.
    This prevents silent degradation where missing graph context
    causes the LLM to hallucinate dependencies.
    """
    print("\n[Node] Neo4j Health Check: Pinging database...")

    uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
    user     = os.getenv("NEO4J_USER",     "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "rosetta_hackathon2026")

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        print(f"[+] Neo4j connected at {uri}")
        return {"neo4j_status": "connected"}

    except Exception as e:
        print(f"[!] Neo4j unreachable at {uri}: {e}")
        return {
            "neo4j_status": "unreachable",
            "validation_passed": False,
            "validation_feedback": (
                f"Neo4j is unreachable at {uri}. "
                "Start the database before running a migration. "
                f"Details: {e}"
            ),
        }


# ==========================================
# 1. AST / GRAPH CONTEXT NODE
# ==========================================
def ast_context_node(state: RosettaState) -> RosettaState:
    migration_id    = state.get("migration_id", "unknown-migration")
    file_path       = state["file_path"]
    target_method   = state["target_method"]
    source_lang     = state.get("source_lang", "java")
    source_framework = state.get("source_framework", "ofbiz")  # Phase 2: parametric framework
    call_graph_csv  = state.get("call_graph_csv_path")          # Phase 4: OpenRewrite fast-path

    print(f"\n[Node] AST/Neo4j Context: Ingesting {target_method} via {source_lang} adapter (framework={source_framework})...")

    AdapterClass = SUPPORTED_SOURCE_LANGS.get(source_lang.lower())
    if not AdapterClass:
        print(f"[!] MIGRATION FAILED — Unsupported source language: {source_lang}")
        return {
            "validation_passed": False,
            "validation_feedback": f"Unsupported source language: {source_lang}",
            "neo4j_context": None,
            "graph_context": "degraded",
        }

    try:
        adapter = AdapterClass()
        context = adapter.ingest_and_get_context(
            migration_id,
            file_path,
            target_method,
            source_framework=source_framework,
            call_graph_csv_path=call_graph_csv,
        )
        return {"neo4j_context": context}
    except Exception as e:
        print(f"[!] MIGRATION FAILED — {source_lang} adapter failed: {e}")
        return {
            "validation_passed": False,
            "validation_feedback": f"{source_lang} adapter failed: {e}",
            "neo4j_context": None,
            "graph_context": "degraded",
        }


# ==========================================
# ROUTING LOGIC
# ==========================================
def route_after_health_check(state: RosettaState) -> str:
    """Short-circuit if Neo4j is unreachable."""
    if state.get("neo4j_status") == "unreachable":
        return END
    return "ast_context_node"


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

# Add nodes
workflow.add_node("neo4j_health_check", neo4j_health_check_node)
workflow.add_node("ast_context_node",   ast_context_node)
workflow.add_node("discovery_agent",    discovery_node)
workflow.add_node("architecture_agent", architecture_node)
workflow.add_node("validator",          validator_node)
workflow.add_node("wrapper",            wrapper_node)

# Set the entry point — health check is always first
workflow.set_entry_point("neo4j_health_check")

# Health check routes to AST context OR short-circuits
workflow.add_conditional_edges(
    "neo4j_health_check",
    route_after_health_check,
    {
        END:               END,
        "ast_context_node": "ast_context_node",
    }
)

# Rest of the pipeline is unchanged
workflow.add_edge("ast_context_node",  "discovery_agent")
workflow.add_edge("discovery_agent",   "architecture_agent")
workflow.add_edge("architecture_agent","validator")

# Autonomous healing loop
workflow.add_conditional_edges(
    "validator",
    route_validation,
    {
        END:                 END,
        "wrapper":           "wrapper",
        "architecture_agent":"architecture_agent",
    }
)
workflow.add_edge("wrapper", END)

rosetta_pipeline = workflow.compile()