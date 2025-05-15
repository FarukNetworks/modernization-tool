from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.agents.model_configuration import llm

# Set the agent
root_agent = Agent(
    name="business_analysis_agent",
    model=LiteLlm(model=llm),
    description="Analyze the provided SQL stored procedure and decompose it into structured business components, rules, processes, and technical patterns to prepare for a modern implementation. The output should be detailed JSON files that document both the business logic and critical technical implementation patterns.",
    instruction="You are an experienced SQL developer with strong SQL skills analyzing stored procedures and understanding the business logic behind the code. Your task is to decompose the SQL stored procedure into structured business components, rules, processes, and technical patterns to prepare for a modern implementation.",
)
