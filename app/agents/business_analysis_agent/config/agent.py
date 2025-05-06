from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.agents.model_configuration import llm

# Set the agent
root_agent = Agent(
    name="business_analysis_agent",
    model=LiteLlm(model=llm),
    description="Modernize the code from SQL to C# Entity Framework Core using .NET9 step by step",
    instruction="You are a modernization agent that can use the stored procedure, analyze the code, transpile the stored procedure to csharp entity framework core using .NET9 and generate the test code for SQL (using tSQLt) and for csharp (using xUnit with integration tests)",
)
