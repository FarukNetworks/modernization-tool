import os
import sys
import json
import uuid
import re
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.agents.business_analysis_agent.prompt import (
    get_prompt,
    get_returnable_objects_prompt,
)
from app.agents.business_analysis_agent.agent import root_agent
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


def analyze_procedure_business_logic(procedure, project_path):
    """Analyze a procedure and generate business logic files"""
    print(f"\nAnalyzing business logic for procedure: {procedure}")

    # Create a new session
    session_service = InMemorySessionService()

    APP_NAME = "Stored Procedure Modernization Analysis"
    USER_ID = "project_owner"
    SESSION_ID = str(uuid.uuid4())
    session = session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    print("Created new session")
    print(f"\tSession ID: {SESSION_ID}")

    # Read the procedure definition
    sql_file_path = os.path.join(project_path, "sql_raw", procedure, f"{procedure}.sql")
    try:
        with open(sql_file_path, "r") as f:
            procedure_definition = f.read()
    except FileNotFoundError:
        print(f"Error: SQL file not found at {sql_file_path}")
        return None

    # Get connection string from project path if available
    connection_string = None
    conn_file_path = os.path.join(project_path, "connection_string.json")
    if os.path.exists(conn_file_path):
        try:
            with open(conn_file_path, "r") as f:
                conn_data = json.load(f)
                connection_string = conn_data.get("connection_string")
        except (json.JSONDecodeError, FileNotFoundError):
            print("Warning: Could not load connection string from project file.")

    # Get dependencies
    dependencies = get_dependencies(procedure, project_path, connection_string)

    # Create analysis directory
    analysis_dir = create_analysis_directory(procedure, project_path)

    # Create and run the agent
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # Collect the final response
    final_response = ""

    # Run the agent to generate business files
    print("Generating business logic files...")
    for event in runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=get_prompt(procedure, procedure_definition, str(dependencies)),
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text
                print(f"Received response from the agent")

    # Extract and save files
    saved_files = extract_files_from_response(final_response, analysis_dir)
    print(f"Created {len(saved_files)} business logic files in {analysis_dir}")

    # Return the session for further use
    return session_service, APP_NAME, USER_ID, SESSION_ID


def analyze_procedure_returnable_objects(
    procedure, session_service, app_name, user_id, session_id, project_path
):
    """Analyze a procedure to generate returnable objects files"""
    print(f"\nAnalyzing returnable objects for procedure: {procedure}")

    # Create analysis directory
    analysis_dir = create_analysis_directory(procedure, project_path)

    # Create prompt for returnable objects analysis
    prompt_text = get_returnable_objects_prompt(procedure, project_path)

    if prompt_text is None:
        print(
            f"Could not generate returnable objects prompt for {procedure}. Skipping this analysis."
        )
        return False

    # Create a content object for the prompt
    from google.genai import types

    content = types.Content(role="user", parts=[types.Part(text=prompt_text)])

    # Create and run the agent
    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_service,
    )

    try:
        # Collect the final response
        final_response = ""

        # Run the agent to generate returnable objects files
        print("Generating returnable objects files...")
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    print(f"Received response from the agent")

        # Extract and save files
        saved_files = extract_files_from_response(final_response, analysis_dir)
        print(f"Created {len(saved_files)} returnable objects files in {analysis_dir}")
        return True

    except Exception as e:
        print(f"Error during returnable objects analysis: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def business_analysis(procedure, project_path):
    """Main entry point - analyze a single procedure generating all 5 JSON files"""
    print(f"\nStarting full business analysis for {procedure}")

    # First run business logic analysis
    session_info = analyze_procedure_business_logic(procedure, project_path)

    if not session_info:
        print(f"Business logic analysis failed for {procedure}")
        return False

    # Then immediately run returnable objects analysis
    session_service, app_name, user_id, session_id = session_info
    success = analyze_procedure_returnable_objects(
        procedure,
        session_service,
        app_name,
        user_id,
        session_id,
        project_path,
    )

    if success:
        print(f"\nComplete business analysis successful for {procedure}")
        return True
    else:
        print(
            f"\nBusiness logic phase completed but returnable objects analysis failed for {procedure}"
        )
        return False


def run_business_analysis(project_path):
    """CLI menu function to select and analyze procedures"""
    print("=== Stored Procedure Business Analysis ===")

    # Get all procedures
    procedures = get_procedures(project_path)

    if not procedures:
        print(f"No procedures found in {os.path.join(project_path, 'sql_raw')}")
        return

    # Display menu
    print("\nAvailable procedures:")
    for i, proc in enumerate(procedures):
        print(f"{i+1}. {proc}")
    print(f"{len(procedures)+1}. Analyze all procedures")
    print(f"{len(procedures)+2}. Return to main menu")

    # Get user selection
    try:
        choice = int(input("\nSelect a procedure to analyze (enter number): "))

        if 1 <= choice <= len(procedures):
            # Analyze single procedure
            procedure = procedures[choice - 1]
            business_analysis(procedure, project_path)
            return

        elif choice == len(procedures) + 1:
            # Analyze all procedures
            completed = 0
            total = len(procedures)

            for procedure in procedures:
                print(f"\nProcessing {procedure} ({completed+1}/{total})...")
                business_analysis(procedure, project_path)
                completed += 1

            print(f"\nBusiness analysis completed for all {completed} procedures.")
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
