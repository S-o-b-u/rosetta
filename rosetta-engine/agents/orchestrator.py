import os
import json
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

# Load environment variables (Google API Key, Neo4j credentials, etc.)
load_dotenv()

# Import the shared state and your agent functions
# (Ensure both agent files import AgentState from a shared location, or define it here)
from discovery_agent import run_discovery_agent
from architecture_agent import run_architecture_agent
from typing import TypedDict

# ==========================================
# 1. DEFINE THE UNIFIED STATE
# ==========================================
class AgentState(TypedDict):
    target_method: str
    raw_java_code: str
    neo4j_context: str
    business_logic: str
    fastapi_code: str  
    openapi_spec: str  

# ==========================================
# 2. BUILD THE LANGGRAPH WORKFLOW
# ==========================================
def build_orchestrator():
    print("[Orchestrator] Initializing Rosetta LangGraph Pipeline...")
    
    # Initialize the graph with our state schema
    workflow = StateGraph(AgentState)
    
    # Add our agent functions as nodes in the graph
    workflow.add_node("discover", run_discovery_agent)
    workflow.add_node("architect", run_architecture_agent)
    
    # Define the execution flow (The Edges)
    workflow.add_edge(START, "discover")      # Start -> Discovery Agent
    workflow.add_edge("discover", "architect") # Discovery -> Architecture Agent
    workflow.add_edge("architect", END)        # Architecture -> End Pipeline
    
    # Compile the graph into a runnable application
    app = workflow.compile()
    return app

# ==========================================
# 3. TEST THE END-TO-END PIPELINE
# ==========================================
if __name__ == "__main__":
    # Mock legacy code input for testing
    mock_java_code = """
    public static Map<String, Object> createInvoiceForOrderAllItems(DispatchContext dctx, Map<String, ? extends Object> context) {
        Delegator delegator = dctx.getDelegator();
        LocalDispatcher dispatcher = dctx.getDispatcher();
        try {
            List<GenericValue> orderItems = EntityQuery.use(delegator).from("OrderItem")
                .where("orderId", context.get("orderId")).queryList();
            if (!orderItems.isEmpty()) context.put("billItems", orderItems);
            
            GenericValue userLogin = EntityQuery.use(delegator).from("UserLogin").where("userLoginId", "system").queryFirst();
            if (userLogin != null) context.put("userLogin", userLogin);
            
            return dispatcher.runSync("createInvoiceForOrder", context);
        } catch (Exception e) { return ServiceUtil.returnError(e.getMessage()); }
    }
    """

    initial_state = {
        "target_method": "createInvoiceForOrderAllItems",
        "raw_java_code": mock_java_code,
        "neo4j_context": "", 
        "business_logic": "",
        "fastapi_code": "",
        "openapi_spec": ""
    }

    # Run the pipeline
    rosetta_app = build_orchestrator()
    print("\n[Orchestrator] Invoking pipeline...")
    
    final_state = rosetta_app.invoke(initial_state)
    
    # Output the final artifacts
    print("\n" + "="*60)
    print("🚀 PIPELINE COMPLETE! FINAL ARTIFACTS:")
    print("="*60)
    
    print("\n--- 1. EXTRACTED BUSINESS LOGIC (JSON) ---")
    print(final_state["business_logic"])
    
    print("\n--- 2. GENERATED FASTAPI MICROSERVICE ---")
    print(final_state["fastapi_code"])
    
    print("\n--- 3. OPENAPI SPECIFICATION ---")
    print(final_state["openapi_spec"])