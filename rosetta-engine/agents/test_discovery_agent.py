import json
from discovery_agent import run_discovery_agent, AgentState

def test_discovery_standalone():
    # 1. Mock the Input State
    mock_state: AgentState = {
        "target_method": "createInvoiceForOrderAllItems",
        "raw_java_code": """
        public static Map<String, Object> createInvoiceForOrderAllItems(DispatchContext dctx, Map<String, ? extends Object> context) {
            Delegator delegator = dctx.getDelegator();
            LocalDispatcher dispatcher = dctx.getDispatcher();
            
            try {
                List<GenericValue> orderItems = EntityQuery.use(delegator).from("OrderItem")
                    .where("orderId", context.get("orderId")).queryList();
                    
                if (!orderItems.isEmpty()) {
                    context.put("billItems", orderItems);
                }
                
                GenericValue userLogin = EntityQuery.use(delegator).from("UserLogin").where("userLoginId", "system").queryFirst();
                if (userLogin != null) {
                    context.put("userLogin", userLogin);
                }
                
                Map<String, Object> result = dispatcher.runSync("createInvoiceForOrder", context);
                return result;
            } catch (GenericEntityException | GenericServiceException e) {
                return ServiceUtil.returnError(e.getMessage());
            }
        }
        """,
        "neo4j_context": "", # This will be fetched by the tool
        "business_logic": "" # This will be populated by the LLM
    }

    # 2. Run the Agent
    print("Starting Discovery Agent Test...")
    final_state = run_discovery_agent(mock_state)

    # 3. Print the Results
    print("\n" + "="*50)
    print("FINAL EXTRACTED BUSINESS LOGIC (JSON Payload):")
    print("="*50)
    
    # We load it from the state and pretty print it just to be sure it's valid JSON
    try:
        parsed_json = json.loads(final_state["business_logic"])
        print(json.dumps(parsed_json, indent=4))
    except json.JSONDecodeError:
         print("ERROR: Output is not valid JSON!")
         print(final_state["business_logic"])
         

if __name__ == "__main__":
    # Make sure you have your OPENAI_API_KEY set in your terminal before running this!
    test_discovery_standalone()