from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.agents.model_configuration import llm

# Set the agent
root_agent = Agent(
    name="integration_test_spec_agent",
    model=LiteLlm(model=llm),
    description="Analyze the stored procedure and provide integration Test Specification for testing the stored procedure.",
    instruction="You are an experienced SQL developer with strong SQL skills analyzing stored procedures and understanding the business logic behind the code.",
)
