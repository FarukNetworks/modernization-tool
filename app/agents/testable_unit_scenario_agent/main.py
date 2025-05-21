import os
import sys
import json
import uuid
import re
import glob
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.agents.testable_unit_scenario_agent.prompt import get_prompt
from app.agents.testable_unit_scenario_agent.agent import root_agent
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
        "business_rules.json",
        "business_functions.json",
        "business_processes.json",
        "returnable_objects.json",
        "process_object_mapping.json",
        "ef_analysis.json",
    ]

    for pattern in required_files:
        files = glob.glob(os.path.join(analysis_dir, pattern))
        if not files:
            print(f"Error: Required file {pattern} not found for {procedure}")
            return False

    return True


def testable_unit_scenarios(procedure, project_path):
    """Main entry point - plan testable unit scenarios for a procedure based on its analysis"""
    print(f"\nStarting testable unit scenarios for {procedure}")

    # Check if all required files exist
    if not check_required_files(procedure, project_path):
        print(
            f"Testable unit scenarios failed for {procedure} due to missing required files"
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

    APP_NAME = "Testable Unit Scenarios Builder"
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

    # Collect the final response
    final_response = ""

    # Get dependencies
    dependencies = get_dependencies(procedure, project_path)

    # Get testable units
    with open(
        f"{project_path}/analysis/{procedure}/testable_units.json",
        "r",
    ) as f:
        testable_units = json.load(f)

    # Run the agent to generate testable unit scenarios
    print("Generating testable unit scenarios...")
    try:
        for event in runner.run(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=get_prompt(
                procedure,
                procedure_definition,
                dependencies,
                project_path,
                testable_unit,
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


def run_testable_unit_scenarios(procedure_name, project_path):
    """CLI menu function to select and analyze procedures"""
    print("=== Testable Unit Scenarios Builder ===")

    # Get all procedures
    procedures = get_procedures(project_path)

    testable_unit_scenarios(procedure_name, project_path)
