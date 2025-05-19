import os
import sys
import inquirer
import json
import pyodbc
import questionary
from questionary import Choice
import sqlparse

# Add the project root directory to sys.path to allow importing from app
# Get the project root directory (3 levels up from this file)
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
sys.path.insert(0, project_root)

# Now import from app package
from app.shared.get_stored_procedures import extract_stored_procedures
from app.shared.scaffold_database import scaffold_database
from app.shared.discover_dependencies import discover_dependencies
from app.shared.run_sql_tests import run_sql_tests
from app.shared.scaffold_templates.create_ef_analysis import (
    analyze_csharp_dependencies,
    run_csharp_dependency_analysis,
)

from app.agents.business_analysis_agent.main import (
    run_business_analysis,
    business_analysis,
)
from app.agents.implementation_planner_agent.main import (
    implementation_planner,
    run_implementation_planner,
)
from app.agents.implementation_executor_agent.main import (
    implementation_executor,
    run_implementation_executor,
)
from app.agents.integration_test_spec_agent.main import (
    create_integration_test_spec,
    run_integration_test_spec,
)
from app.agents.sql_test_generation_agent.main import (
    generate_sql_test,
    run_sql_test_generation,
)
from app.agents.csharp_test_generation_agent.main import (
    generate_csharp_test,
    run_csharp_test_generation,
    generate_csharp_tests_cli,
)
from app.agents.mcp_agent.main import (
    run_implementation_executor as run_mcp_implementation_executor,
)


def create_project_directory(project_name):
    """Create a new project directory in the output folder."""
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "output",
    )
    project_path = os.path.join(output_dir, project_name)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if os.path.exists(project_path):
        print(f"Project '{project_name}' already exists!")
        return None, project_name  # Return both values, but with None for project_path

    os.makedirs(project_path)
    print(f"Project '{project_name}' created successfully at {project_path}")
    return project_path, project_name


def get_existing_projects():
    """Get the list of existing projects in the output folder."""
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "output",
    )

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        return []

    return [
        d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))
    ]


def select_or_create_project():
    """Ask the user to select an existing project or create a new one."""
    existing_projects = get_existing_projects()

    if existing_projects:
        choices = existing_projects + ["Create a new project"]

        questions = [
            inquirer.List(
                "project_action",
                message="Select existing project or create a new one:",
                choices=choices,
            ),
        ]

        answers = inquirer.prompt(questions)
        selected = answers["project_action"]

        if selected == "Create a new project":
            return prompt_for_new_project()
        else:
            project_name = selected
            output_dir = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "output",
            )
            project_path = os.path.join(output_dir, selected)
            return project_path, project_name
    else:
        return prompt_for_new_project()


def prompt_for_new_project():
    """Prompt the user to enter a name for a new project."""
    questions = [
        inquirer.Text("project_name", message="Enter project name"),
    ]

    answers = inquirer.prompt(questions)
    project_name = answers["project_name"]

    return create_project_directory(project_name)


def prompt_for_connection_string():
    """Prompt the user to enter a connection string."""
    questions = [
        inquirer.Text(
            "connection_string",
            message="Enter database connection string",
            validate=lambda _, x: len(x) > 0,
        ),
    ]

    answers = inquirer.prompt(questions)
    return answers["connection_string"]


def save_connection_string(project_path, connection_string):
    """Save the connection string to a config file in the project directory."""
    config_file = os.path.join(project_path, "connection_string.json")

    config = {"connection_string": connection_string}

    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)

    print(f"Connection string saved to {config_file}")


def has_existing_connection_string(project_path):
    """Check if the project already has a connection string configured."""
    config_file = os.path.join(project_path, "connection_string.json")
    return os.path.exists(config_file)


def get_existing_connection_string(project_path):
    """Get the existing connection string from the project config."""
    config_file = os.path.join(project_path, "connection_string.json")

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            return config.get("connection_string", "")
    except (json.JSONDecodeError, FileNotFoundError):
        return ""


def prompt_for_next_action(project_path, connection_string, project_name):
    """Ask the user what action they want to perform next."""
    questions = [
        inquirer.List(
            "next_action",
            message="What would you like to do next?",
            choices=[
                "Prepare Stored Procedures",
                "Scaffold Database",
                "Discover Dependencies",
                "Business Analysis",
                "Csharp Dependency Analysis",
                "Implementation Planner",
                "Implementation Executor",
                "MCP Implementation Executor",
                "Integration Test Specification",
                "Generate SQL Tests",
                "Run SQL Tests",
                "Create Csharp Tests",
                "Exit",
            ],
        ),
    ]

    answers = inquirer.prompt(questions)
    selected = answers["next_action"]

    if selected == "Prepare Stored Procedures":
        extract_stored_procedures(project_path, connection_string)
        # After extraction, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Scaffold Database":
        scaffold_database("csharp-code", project_name)
        # After scaffolding, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Discover Dependencies":
        discover_dependencies(connection_string, project_name)
        # After discovery, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Business Analysis":
        # Get list of procedures to analyze
        procedures = [
            folder
            for folder in os.listdir(os.path.join(project_path, "sql_raw"))
            if os.path.isdir(os.path.join(project_path, "sql_raw", folder))
        ]

        # Ask if user wants to run full menu or analyze a specific procedure
        if procedures:
            choices = ["Show full menu"] + procedures + ["Return to main menu"]
            questions = [
                inquirer.List(
                    "analysis_choice",
                    message="What would you like to analyze?",
                    choices=choices,
                ),
            ]
            analysis_answer = inquirer.prompt(questions)
            selected_analysis = analysis_answer["analysis_choice"]

            if selected_analysis == "Show full menu":
                # Run business analysis using the full menu
                run_business_analysis(project_path)
            elif selected_analysis == "Return to main menu":
                pass
            else:
                # Analyze the selected procedure directly
                business_analysis(selected_analysis, project_path)
        else:
            print("No procedures found. Please run 'Prepare Stored Procedures' first.")

        # After analysis, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Csharp Dependency Analysis":
        # Get list of procedures for C# dependency analysis
        procedures = [
            folder
            for folder in os.listdir(os.path.join(project_path, "sql_raw"))
            if os.path.isdir(os.path.join(project_path, "sql_raw", folder))
        ]

        # Ask if user wants to run full menu or analyze a specific procedure
        if procedures:
            choices = ["Show full menu"] + procedures + ["Return to main menu"]
            questions = [
                inquirer.List(
                    "csharp_analysis_choice",
                    message="Which procedure would you like to analyze?",
                    choices=choices,
                ),
            ]
            csharp_analysis_answer = inquirer.prompt(questions)
            selected_csharp_analysis = csharp_analysis_answer["csharp_analysis_choice"]

            if selected_csharp_analysis == "Show full menu":
                # Run C# dependency analysis using the full menu
                run_csharp_dependency_analysis(project_path)
            elif selected_csharp_analysis == "Return to main menu":
                pass
            else:
                # Analyze the selected procedure directly
                analyze_csharp_dependencies(selected_csharp_analysis, project_path)
        else:
            print("No procedures found. Please run 'Prepare Stored Procedures' first.")

        # After analysis, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Implementation Planner":
        # Get list of procedures to plan implementation for
        procedures = [
            folder
            for folder in os.listdir(os.path.join(project_path, "sql_raw"))
            if os.path.isdir(os.path.join(project_path, "sql_raw", folder))
        ]

        # Ask if user wants to run full menu or plan a specific procedure
        if procedures:
            choices = ["Show full menu"] + procedures + ["Return to main menu"]
            questions = [
                inquirer.List(
                    "planner_choice",
                    message="What would you like to plan implementation for?",
                    choices=choices,
                ),
            ]
            planner_answer = inquirer.prompt(questions)
            selected_procedure = planner_answer["planner_choice"]

            if selected_procedure == "Show full menu":
                # Run implementation planner using the full menu
                run_implementation_planner(project_path)
            elif selected_procedure == "Return to main menu":
                pass
            else:
                # Plan implementation for the selected procedure directly
                implementation_planner(selected_procedure, project_path)
        else:
            print("No procedures found. Please run 'Prepare Stored Procedures' first.")

        # After planning, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Implementation Executor":
        # Get list of procedures to execute implementation for
        procedures = [
            folder
            for folder in os.listdir(os.path.join(project_path, "sql_raw"))
            if os.path.isdir(os.path.join(project_path, "sql_raw", folder))
        ]

        # Ask if user wants to run full menu or execute implementation for a specific procedure
        if procedures:
            choices = ["Show full menu"] + procedures + ["Return to main menu"]
            questions = [
                inquirer.List(
                    "executor_choice",
                    message="What would you like to execute implementation for?",
                    choices=choices,
                ),
            ]
            executor_answer = inquirer.prompt(questions)
            selected_procedure = executor_answer["executor_choice"]

            if selected_procedure == "Show full menu":
                # Run implementation executor using the full menu
                run_implementation_executor(project_path)
            elif selected_procedure == "Return to main menu":
                pass
            else:
                # Execute implementation for the selected procedure directly
                implementation_executor(selected_procedure, project_path)
        else:
            print("No procedures found. Please run 'Prepare Stored Procedures' first.")

        # After execution, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "MCP Implementation Executor":
        # Get list of procedures to execute implementation for
        procedures = [
            folder
            for folder in os.listdir(os.path.join(project_path, "sql_raw"))
            if os.path.isdir(os.path.join(project_path, "sql_raw", folder))
        ]

        # Ask if user wants to run full menu or execute implementation for a specific procedure
        if procedures:
            choices = procedures + ["Return to main menu"]
            questions = [
                inquirer.List(
                    "mcp_executor_choice",
                    message="Which procedure would you like to implement with MCP?",
                    choices=choices,
                ),
            ]
            mcp_executor_answer = inquirer.prompt(questions)
            selected_procedure = mcp_executor_answer["mcp_executor_choice"]

            if selected_procedure == "Return to main menu":
                pass
            else:
                # Execute implementation for the selected procedure using MCP agent
                print(
                    f"Running MCP Implementation Executor for {selected_procedure}..."
                )
                import asyncio

                asyncio.run(
                    run_mcp_implementation_executor(selected_procedure, project_path)
                )
        else:
            print("No procedures found. Please run 'Prepare Stored Procedures' first.")

        # After execution, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Integration Test Specification":
        # Get list of procedures for integration test specification
        procedures = [
            folder
            for folder in os.listdir(os.path.join(project_path, "sql_raw"))
            if os.path.isdir(os.path.join(project_path, "sql_raw", folder))
        ]

        # Ask if user wants to run full menu or generate test specs for a specific procedure
        if procedures:
            choices = ["Show full menu"] + procedures + ["Return to main menu"]
            questions = [
                inquirer.List(
                    "test_spec_choice",
                    message="Which procedure would you like to generate test specifications for?",
                    choices=choices,
                ),
            ]
            test_spec_answer = inquirer.prompt(questions)
            selected_procedure = test_spec_answer["test_spec_choice"]

            if selected_procedure == "Show full menu":
                # Run integration test specification using the full menu
                run_integration_test_spec(project_path)
            elif selected_procedure == "Return to main menu":
                pass
            else:
                # Generate test specifications for the selected procedure directly
                create_integration_test_spec(selected_procedure, project_path)
        else:
            print("No procedures found. Please run 'Prepare Stored Procedures' first.")

        # After test specification, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Generate SQL Tests":
        # Get list of procedures for SQL test generation
        procedures = [
            folder
            for folder in os.listdir(os.path.join(project_path, "sql_raw"))
            if os.path.isdir(os.path.join(project_path, "sql_raw", folder))
        ]

        # Ask if user wants to run full menu or generate tests for a specific procedure
        if procedures:
            choices = ["Show full menu"] + procedures + ["Return to main menu"]
            questions = [
                inquirer.List(
                    "sql_test_choice",
                    message="Which procedure would you like to generate SQL tests for?",
                    choices=choices,
                ),
            ]
            sql_test_answer = inquirer.prompt(questions)
            selected_procedure = sql_test_answer["sql_test_choice"]

            if selected_procedure == "Show full menu":
                # Run SQL test generation using the full menu
                run_sql_test_generation(project_path)
            elif selected_procedure == "Return to main menu":
                pass
            else:
                # Generate SQL tests for the selected procedure directly
                generate_sql_test(selected_procedure, project_path)
        else:
            print("No procedures found. Please run 'Prepare Stored Procedures' first.")

        # After SQL test generation, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Run SQL Tests":
        # Implementation of running SQL tests
        print("Running SQL tests...")
        run_sql_tests(project_path, connection_string)
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Create Csharp Tests":
        # Use the simplified CLI function
        generate_csharp_tests_cli(project_path)

        # After C# test generation, ask again what to do next
        prompt_for_next_action(project_path, connection_string, project_name)
    elif selected == "Exit":
        print("Exiting. Goodbye!")
        sys.exit(0)


def main():
    """Main function to run the CLI."""
    print("Welcome to the Project Management CLI!")

    project_path, project_name = select_or_create_project()

    if project_path:
        print(f"Working with project at: {project_path}")

        # Check if connection string already exists
        if has_existing_connection_string(project_path):
            connection_string = get_existing_connection_string(project_path)
            print(f"Using existing connection string: {connection_string}")
        else:
            # Prompt for connection string
            connection_string = prompt_for_connection_string()

            # Save connection string to project config
            save_connection_string(project_path, connection_string)

        # Ask what action to perform next
        prompt_for_next_action(project_path, connection_string, project_name)
    else:
        print("Project creation failed or was cancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
