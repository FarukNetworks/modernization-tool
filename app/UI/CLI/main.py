import os
import sys
import inquirer
import json
import pyodbc
import questionary
from questionary import Choice
import sqlparse
import sys
import os

# Add the parent directory to sys.path to allow importing from app
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from shared.get_stored_procedures import extract_stored_procedures
from shared.scaffold_database import scaffold_database
from shared.discover_dependencies import discover_dependencies


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
        discover_dependencies(connection_string)
        # After discovery, ask again what to do next
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
