from dotenv import load_dotenv
import os

load_dotenv()

# Set the agent Model
llm_config = os.getenv("LLM_CONFIG")
llm = None

if llm_config == "openai":
    llm = "openai/o3-mini"
elif llm_config == "gemini":
    llm = "google/gemini-1.5-flash"
elif llm_config == "anthropic":
    llm = "anthropic/claude-3-7-sonnet-latest"
elif llm_config == "bedrock":
    llm = "bedrock/us.meta.llama3-3-70b-instruct-v1:0"
