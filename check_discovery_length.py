import sys
import os
import json

sys.path.append(os.path.abspath('rosetta-engine'))
from core.agents import discovery_node

state = {
    "target_method": "actionPerformed",
    "source_framework": "swing_java",
    "java_code": open("ATM-Simulator-System/src/ASimulatorSystem/Login.java").read(),
    "neo4j_context": {"dummy": "data" * 1000},
}

try:
    import core.agents
    
    class MockChain:
        def invoke(self, kwargs):
            prompt_str = core.agents.prompt.format(**kwargs)
            
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            tokens = enc.encode(prompt_str)
            print(f"Discovery Token count: {len(tokens)}")
            
            class DummyResponse:
                content = "```json\n{}\n```"
            return DummyResponse()
            
    core.agents.chain = MockChain()
    
    discovery_node(state)
except Exception as e:
    import traceback
    traceback.print_exc()
