import os
import sys
import json
import uuid
import re
import glob
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.agents.implementation_planner_agent.prompt import get_prompt
from app.agents.implementation_planner_agent.agent import root_agent
from app.shared.get_dependencies import get_dependencies

# Add parent directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_procedures(project_path):
    """Get all folder names from sql_raw directory"""
    procedures = []
    sql_raw_dir = os.path.join(project_path, "sql_raw")

    if os.path.exists(sql_raw_dir):
        procedures = [
            folder
            for folder in os.listdir(sql_raw_dir)
            if os.path.isdir(os.path.join(sql_raw_dir, folder))
        ]
    return procedures


def create_analysis_directory(procedure, project_path):
    """Create analysis directory for the selected procedure"""
    analysis_dir = os.path.join(project_path, "analysis", procedure)
    os.makedirs(analysis_dir, exist_ok=True)
    return analysis_dir


def save_json_file(file_path, content):
    """Save the file content to the specified path"""
    # Create the full directory path
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save the file content
    with open(file_path, "w") as f:
        f.write(content)


def extract_files_from_response(result, analysis_dir):
    """Extract JSON files from the model response and save them"""
    file_paths = []

    # Extract file paths and contents
    for match in re.finditer(r"FILE: (.*?)\n```json\n(.*?)```", result, re.DOTALL):
        file_path = match.group(1).strip()
        file_content = match.group(2).strip()

        # Get just the filename without any path
        filename = os.path.basename(file_path)

        # Save the file content
        full_path = os.path.join(analysis_dir, filename)
        save_json_file(full_path, file_content)
        file_paths.append(filename)

    return file_paths


def check_required_files(procedure, project_path):
    """Check if all required files for implementation planning exist"""
    analysis_dir = os.path.join(project_path, "analysis", procedure)

    if not os.path.exists(analysis_dir):
        print(f"Error: Analysis directory not found for {procedure}")
        return False

    required_files = [
        "*_business_rules.json",
        "*_business_functions.json",
        "*_business_processes.json",
        "*_returnable_objects.json",
        "*_process_object_mapping.json",
        "*_ef_analysis.json",
    ]

    for pattern in required_files:
        files = glob.glob(os.path.join(analysis_dir, pattern))
        if not files:
            print(f"Error: Required file {pattern} not found for {procedure}")
            return False

    # Check if the Abstractions/Repositories folder exists
    abstractions_path = os.path.join(
        project_path, "csharp-code", "Abstractions", "Repositories"
    )
    if not os.path.exists(abstractions_path):
        print(
            f"Error: Abstractions/Repositories folder not found at {abstractions_path}"
        )
        return False

    return True


def implementation_planner(procedure, project_path):
    """Main entry point - plan implementation for a procedure based on its analysis"""
    print(f"\nStarting implementation planning for {procedure}")

    # Check if all required files exist
    if not check_required_files(procedure, project_path):
        print(
            f"Implementation planning failed for {procedure} due to missing required files"
        )
        return False

    # Read the procedure definition
    sql_file_path = os.path.join(project_path, "sql_raw", procedure, f"{procedure}.sql")
    try:
        with open(sql_file_path, "r") as f:
            procedure_definition = f.read()
    except FileNotFoundError:
        print(f"Error: SQL file not found at {sql_file_path}")
        return False

    # Create a new session
    session_service = InMemorySessionService()

    APP_NAME = "Stored Procedure Implementation Planner"
    USER_ID = "project_owner"
    SESSION_ID = str(uuid.uuid4())
    session = session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    print("Created new session")
    print(f"\tSession ID: {SESSION_ID}")

    # Create analysis directory
    analysis_dir = create_analysis_directory(procedure, project_path)

    # Create and run the agent
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # Get the schema name (e.g., "dbo" from "dbo.usp_procedure")
    schema_name = "dbo"
    if "." in procedure:
        schema_name = procedure.split(".")[0]

    # Collect the final response
    final_response = ""

    # Run the agent to generate implementation plan
    print("Generating implementation plan...")
    try:
        for event in runner.run(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=get_prompt(
                schema_name, procedure, procedure_definition, project_path
            ),
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    print(f"Received response from the agent")

                    # Debug: Check if the response contains the expected file pattern
                    if "FILE:" in final_response and "```json" in final_response:
                        print("Response contains file markers")
                    else:
                        print(
                            "WARNING: Response does not contain expected file markers"
                        )
                        print("First 150 chars of response:", final_response[:150])

        # Extract and save files
        saved_files = extract_files_from_response(final_response, analysis_dir)
        print(f"Created {len(saved_files)} implementation plan files in {analysis_dir}")
        return True

    except Exception as e:
        print(f"Error during implementation planning: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def run_implementation_planner(project_path):
    """CLI menu function to select and analyze procedures"""
    print("=== Stored Procedure Implementation Planner ===")

    # Get all procedures
    procedures = get_procedures(project_path)

    if not procedures:
        print(f"No procedures found in {os.path.join(project_path, 'sql_raw')}")
        return

    # Display menu
    print("\nAvailable procedures:")
    for i, proc in enumerate(procedures):
        print(f"{i+1}. {proc}")
    print(f"{len(procedures)+1}. Plan all procedures")
    print(f"{len(procedures)+2}. Return to main menu")

    # Get user selection
    try:
        choice = int(input("\nSelect a procedure to plan (enter number): "))

        if 1 <= choice <= len(procedures):
            # Plan single procedure
            procedure = procedures[choice - 1]
            implementation_planner(procedure, project_path)
            return

        elif choice == len(procedures) + 1:
            # Plan all procedures
            completed = 0
            total = len(procedures)

            for procedure in procedures:
                print(f"\nProcessing {procedure} ({completed+1}/{total})...")
                implementation_planner(procedure, project_path)
                completed += 1

            print(
                f"\nImplementation planning completed for all {completed} procedures."
            )
            return

        elif choice == len(procedures) + 2:
            print("Returning to main menu...")
            return

        else:
            print("Invalid choice. Please try again.")
            return

    except ValueError:
        print("Please enter a valid number.")
        return

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return
