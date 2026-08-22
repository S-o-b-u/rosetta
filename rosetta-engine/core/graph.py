from langgraph.graph import StateGraph, END
from core.state import RosettaState
# Import the REAL LangChain agents we built!
from core.agents import discovery_node, architecture_node
from core.validator import validator_node
from core.wrapper import wrapper_node

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
workflow.add_node("discovery_agent", discovery_node)
workflow.add_node("architecture_agent", architecture_node)
workflow.add_node("validator", validator_node)
workflow.add_node("wrapper", wrapper_node)

# Set the flow
workflow.set_entry_point("discovery_agent")
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