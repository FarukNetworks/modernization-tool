from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.agents.model_configuration import llm

# Set the agent
root_agent = Agent(
    name="testable_unit_scenario_agent",
    model=LiteLlm(model=llm),
    description="You are an expert in creating testable unit scenarios from a given set of testable units.",
    instruction="You will be provided with the stored procedure definition, business functions, business processes, testable units, returnable objects, and process object mapping. You will need to create a testable unit scenario in JSON format that will help support teams explain the technical logic to non-technical users.",
)
