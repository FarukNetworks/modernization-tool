# agent.py (modify get_tools_async and other parts as needed)
# ./adk_agent_samples/mcp_agent/agent.py
import asyncio
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import (
    InMemoryArtifactService,
)  # Optional
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    SseServerParams,
    StdioServerParameters,
)
import os
from app.agents.mcp_implementation_executor_agent.prompt import get_prompt

# Load environment variables from .env file
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


# Get System Prompt
with open(
    "app/agents/mcp_implementation_executor_agent/system_prompt.txt", "r"
) as file:
    system_prompt = file.read()


# --- Step 1: Agent Definition ---
async def get_agent_async():
    """Creates an ADK Agent equipped with tools from the MCP Server."""
    tools, exit_stack = await MCPToolset.from_server(
        # Use StdioServerParameters for local process communication
        connection_params=StdioServerParameters(
            command="npx",  # Command to run the server
            args=[
                "-y",  # Arguments for the command
                "@modelcontextprotocol/server-filesystem",
                "/Users/farukdelic/Desktop/symphony/projects/modernization-tool/app/output",
            ],
        )
        # For remote servers, you would use SseServerParams instead:
        # connection_params=SseServerParams(url="http://remote-server:port/path", headers={...})
    )
    print(f"Fetched {len(tools)} tools from MCP server.")
    root_agent = LlmAgent(
        model=LiteLlm(model=llm),
        name="mcp_implementation_executor_agent",
        instruction=system_prompt,
        tools=tools,  # Provide the MCP tools to the ADK agent
    )
    return root_agent, exit_stack


# --- Step 2: Main Execution Logic ---
async def async_main():
    session_service = InMemorySessionService()
    # Artifact service might not be needed for this example
    artifacts_service = InMemoryArtifactService()

    session = session_service.create_session(
        state={}, app_name="mcp_implementation_executor_agent", user_id="user_mcp"
    )

    query = get_prompt(
        procedure_name="get_all_customers",
        procedure_definition="SELECT * FROM customers",
        project_path="/Users/farukdelic/Desktop/symphony/projects/modernization-tool/app",
    )
    print(f"User Query: '{query}'")
    content = types.Content(role="user", parts=[types.Part(text=query)])

    root_agent, exit_stack = await get_agent_async()

    runner = Runner(
        app_name="mcp_implementation_executor_agent",
        agent=root_agent,
        artifact_service=artifacts_service,  # Optional
        session_service=session_service,
    )

    print("Running agent...")
    events_async = runner.run_async(
        session_id=session.id, user_id=session.user_id, new_message=content
    )

    async for event in events_async:
        print(f"Event received: {event}")

    # Crucial Cleanup: Ensure the MCP server process connection is closed.
    print("Closing MCP server connection...")
    await exit_stack.aclose()
    print("Cleanup complete.")


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except Exception as e:
        print(f"An error occurred: {e}")
