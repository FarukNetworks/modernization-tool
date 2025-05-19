from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.agents.model_configuration import llm

# Set the agent
root_agent = Agent(
    name="csharp_test_generation_agent",
    model=LiteLlm(model=llm),
    description="""
Generate a xUnit test for a C# implementation
""",
    instruction="""
You are an experienced C# developer with strong C# skills analyzing test specification and providing C# unit test code testing the C# API endpoints and repository.
""",
)
