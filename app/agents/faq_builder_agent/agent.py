from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.agents.model_configuration import llm

# Set the agent
root_agent = Agent(
    name="faq_builder_agent",
    model=LiteLlm(model=llm),
    description="You are an expert in creating FAQ documents from a given set of questions and answers.",
    instruction="You will be provided with the stored procedure definition, business functions, business processes, testable units, returnable objects, and process object mapping. You will need to create a FAQ document in JSON format that will help support teams explain the technical logic to non-technical users.",
)
