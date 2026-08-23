import sys
import os

sys.path.append(os.path.abspath('rosetta-engine'))
from core.agents import architecture_node

state = {
    "target_method": "actionPerformed",
    "source_framework": "swing_java",
    "logic_json": open("modern-invoices/atm-login/actionPerformed_logic.json").read(),
    "validation_feedback": None
}

try:
    # We mock out the actual llm call in architecture_node to just print the prompt length
    import core.agents
    
    # Monkey-patch chain invoke to just return length
    class MockChain:
        def invoke(self, kwargs):
            prompt_str = core.agents.prompt.format(**kwargs)
            
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            tokens = enc.encode(prompt_str)
            print(f"Token count: {len(tokens)}")
            
            class DummyResponse:
                content = "```python\npass\n```"
            return DummyResponse()
            
    core.agents.chain = MockChain()
    
    architecture_node(state)
except Exception as e:
    import traceback
    traceback.print_exc()
