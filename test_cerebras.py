import os
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gemma-4-31b",
    api_key=os.getenv("CEREBRAS_API_KEY"),
    base_url="https://api.cerebras.ai/v1",
    temperature=0.1,
)

try:
    print(llm.invoke("Hello, who are you?").content)
except Exception as e:
    print(f"Error: {e}")
