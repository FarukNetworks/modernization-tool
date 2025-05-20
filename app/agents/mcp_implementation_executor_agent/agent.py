import os
from google.adk.agents import Agent
from contextlib import AsyncExitStack
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
    SseServerParams,
)
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

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

with open(
    "app/agents/mcp_implementation_executor_agent/system_prompt.txt", "r"
) as file:
    system_prompt = file.read()


async def create_agent():
    print("🟢 Initializing agent...")

    try:

        common_exit_stack = AsyncExitStack()

        # Start local MCP tool
        try:
            print("🔧 Starting local MCP tool...")
            local_tools, _ = await MCPToolset.from_server(
                connection_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        "/Users/farukdelic/Desktop/symphony/projects/modernization-tool/app/output",
                    ],
                ),
                async_exit_stack=common_exit_stack,
            )
            print(f"✅ Loaded local tools: {len(local_tools)}")
        except Exception as e:
            print(f"❌ Error starting local MCP tool: {e}")
            local_tools = []

        # Start remote MCP tool
        try:
            print("🌐 Starting remote MCP tool...")
            remote_tools, _ = await MCPToolset.from_server(
                connection_params=SseServerParams(url="http://localhost:8080/sse"),
                async_exit_stack=common_exit_stack,
            )
            print(f"✅ Loaded remote tools: {len(remote_tools)}")
        except Exception as e:
            print(f"❌ Error starting remote MCP tool: {e}")
            remote_tools = []

        tools = [*local_tools, *remote_tools]
        if not tools:
            raise RuntimeError("No tools available. Agent will not start.")

        agent = Agent(
            model=LiteLlm(model=llm),
            name="mcp_implementation_executor_agent",
            instruction=system_prompt,
            tools=tools,
        )

        print("✅ Agent created successfully.")
        return agent, common_exit_stack

    except Exception as e:
        print(f"🔥 Failed to initialize agent: {e}")
        return None, None


root_agent = create_agent()
