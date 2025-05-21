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
import time

# Load environment variables from .env file
load_dotenv()

# Set the agent Model
llm_config = os.getenv("LLM_CONFIG")
llm = None

if llm_config == "openai":
    llm = "openai/gpt-4.1-mini"
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
async def get_agent_async(project_path):
    """
    Creates an ADK Agent equipped with tools from the MCP Server.

    Args:
        project_path: Path to the project directory
    """
    # Extract the base output directory from the project_path
    # The project_path is like /path/to/app/output/ProjectName
    # We need /path/to/app/output for the MCP server

    print("--------------------------------")
    print(f"Project path: {project_path}")
    print("--------------------------------")

    tools, exit_stack = await MCPToolset.from_server(
        # Use StdioServerParameters for local process communication
        connection_params=StdioServerParameters(
            command="npx",  # Command to run the server
            args=[
                "-y",  # Arguments for the command
                "@modelcontextprotocol/server-filesystem",
                project_path,
            ],
        )
        # For remote servers, you would use SseServerParams instead:
        # connection_params=SseServerParams(url="http://remote-server:port/path", headers={...})
    )
    print(f"Fetched {len(tools)} tools from MCP server.")
    root_agent = LlmAgent(
        model=LiteLlm(model=llm),
        name="mcp_implementation_executor_agent",
        description="You are an implementation agent that can use MCP to read, write and modify files. Your exsistance is to fully implement the csharp code of the given stored procedure",
        instruction=system_prompt,
        tools=tools,  # Provide the MCP tools to the ADK agent
    )
    return root_agent, exit_stack


# --- New function to implement stored procedures ---
async def run_mcp_implementation_executor(procedure_name, project_path):
    """
    Execute implementation for a specific stored procedure using MCP

    Args:
        procedure_name: Name of the procedure to implement
        project_path: Path to the project directory
    """
    # Read the stored procedure definition
    sql_file_path = os.path.join(
        project_path, "sql_raw", procedure_name, f"{procedure_name}.sql"
    )

    procedure_definition = ""
    if os.path.exists(sql_file_path):
        with open(sql_file_path, "r") as f:
            procedure_definition = f.read()
    else:
        print(f"Error: Could not find SQL definition at {sql_file_path}")
        return

    # Generate the prompt with the procedure details
    query = get_prompt(
        procedure_name=procedure_name,
        procedure_definition=procedure_definition,
        project_path=project_path,
    )

    # Set up session services
    session_service = InMemorySessionService()
    artifacts_service = InMemoryArtifactService()

    unique_code = int(time.time())

    session = session_service.create_session(
        state={},
        app_name=f"mcp_implementation_executor_agent_{unique_code}",
        user_id=f"user_mcp_{unique_code}",
    )

    print(f"Implementing procedure: '{procedure_name}'")
    content = types.Content(role="user", parts=[types.Part(text=query)])

    root_agent, exit_stack = await get_agent_async(project_path)

    runner = Runner(
        app_name=f"mcp_implementation_executor_agent_{unique_code}",
        agent=root_agent,
        artifact_service=artifacts_service,
        session_service=session_service,
    )

    print("Running MCP implementation executor agent...")
    events_async = runner.run_async(
        session_id=session.id, user_id=session.user_id, new_message=content
    )

    async for event in events_async:
        print(f"Event received: {event}")

    # Crucial Cleanup: Ensure the MCP server process connection is closed.
    print("Closing MCP server connection...")
    await exit_stack.aclose()
    print("Implementation complete.")
