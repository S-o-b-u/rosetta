import json
from architecture_agent import run_architecture_agent, AgentState


def test_architecture_standalone():
    # 1. Mock the Input State (Simulating the output from the Discovery Agent)
    mock_business_logic = {
        "service_name": "createInvoiceForOrderAllItems",
        "trigger": "Service invocation / API call",
        "inputs": [
            {"name": "orderId", "type": "String", "required": True},
            {"name": "billItems", "type": "List", "required": False},
            {"name": "userLogin", "type": "GenericValue", "required": False}
        ],
        "database_interactions": [
            {"table": "OrderItem", "action": "READ", "condition": "orderId equals the input orderId"},
            {"table": "UserLogin", "action": "READ", "condition": "userLoginId equals 'system'"}
        ],
        "business_rules_sequence": [
            "Fetch all OrderItem records associated with the input orderId from the database.",
            "If any OrderItem records exist, place them into the context as billItems.",
            "Fetch the system UserLogin record where userLoginId is 'system'.",
            "If the system UserLogin record exists, place it into the context as userLogin.",
            "Synchronously dispatch and execute the 'createInvoiceForOrder' service passing the modified context.",
            "Return the result of the service execution, or an error message if an exception occurs."
        ]
    }

    mock_state: AgentState = {
        "target_method": "createInvoiceForOrderAllItems",
        "raw_java_code": "", # Not needed for this agent
        "neo4j_context": "", # Not needed for this agent
        "business_logic": json.dumps(mock_business_logic),
        "fastapi_code": "",
        "openapi_spec": ""
    }

    # 2. Run the Agent
    print("Starting Architecture Agent Test...")
    final_state = run_architecture_agent(mock_state)

    # 3. Print the Results
    print("\n" + "="*50)
    print("FINAL GENERATED FASTAPI CODE:")
    print("="*50)
    print(final_state["fastapi_code"])
    
    print("\n" + "="*50)
    print("FINAL GENERATED OPENAPI SPEC (YAML):")
    print("="*50)
    print(final_state["openapi_spec"])

if __name__ == "__main__":
    test_architecture_standalone()