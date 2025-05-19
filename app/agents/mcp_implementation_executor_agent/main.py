import os
import asyncio
from typing import Optional
from .agent import create_agent


async def run_implementation_executor(procedure_name: str, project_path: str) -> None:
    """
    Run the MCP Implementation Executor agent to convert SQL stored procedure to C# implementation.

    Args:
        procedure_name: The name of the stored procedure to implement
        project_path: The path to the project directory
    """
    print(f"Starting MCP Implementation Executor for procedure: {procedure_name}")

    # Initialize the agent
    agent, exit_stack = await create_agent()
    if not agent:
        print("Failed to initialize MCP Implementation Executor agent")
        return

    try:
        # Construct the prompt for the agent
        prompt = f"""
I need you to implement the SQL stored procedure '{procedure_name}' as C# business logic.

1. Read the SQL code from {project_path}/sql_raw/{procedure_name}/
2. Analyze the business logic in the stored procedure
3. Implement an equivalent C# implementation
4. Save the implementation to {project_path}/csharp-code/Services/{procedure_name}/
5. Ensure the implementation follows clean architecture principles

Please start by reading the SQL files and then proceed with the implementation.
"""

        # Run the agent with the prompt
        response = await agent.generate_content(prompt)
        print(f"Agent response: {response.text}")

    except Exception as e:
        print(f"Error while running MCP Implementation Executor: {e}")
    finally:
        # Clean up resources
        if exit_stack:
            await exit_stack.aclose()


# Synchronous wrapper for easier calling
def mcp_implementation_executor(procedure_name: str, project_path: str) -> None:
    """
    Synchronous wrapper for run_implementation_executor
    """
    asyncio.run(run_implementation_executor(procedure_name, project_path))
