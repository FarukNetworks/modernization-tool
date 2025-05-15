from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.agents.model_configuration import llm

# Set the agent
root_agent = Agent(
    name="implementation_planner_agent",
    model=LiteLlm(model=llm),
    description="Detailed implementation plan for migrating a SQL stored procedure to a modern, testable C# application following the repository pattern.",
    instruction="You are an experienced C# developer meticulously following best practices for C# and .NET 9. You are also an expert of the stored procedure.",
)
