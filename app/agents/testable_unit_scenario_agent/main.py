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


def save_json_file(file_path, content):
    """Save the file content to the specified path"""
    # Create the full directory path
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save the file content
    with open(file_path, "w") as f:
        f.write(content)


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
    import re

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

    # Get dependencies
    dependencies = get_dependencies(procedure, project_path)

    # Get testable units
    testable_units_path = os.path.join(
        project_path, "analysis", procedure, "testable_units.json"
    )
    try:
        with open(testable_units_path, "r") as f:
            testable_units_data = json.load(f)
            testable_units = testable_units_data.get("testableUnits", [])
    except FileNotFoundError:
        print(f"Error: Testable units file not found at {testable_units_path}")
        return False

    # Variable to store all scenarios for all units
    all_scenarios = {"testableUnitScenarios": []}

    # Process each testable unit
    for unit_index, testable_unit in enumerate(testable_units):
        print(
            f"Processing testable unit {unit_index + 1}/{len(testable_units)}: {testable_unit['name']}"
        )

        # Create a new session for each unit
        session_service = InMemorySessionService()
        APP_NAME = "Testable Unit Scenarios Builder"
        USER_ID = "project_owner"
        SESSION_ID = str(uuid.uuid4())
        session = session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )

        # Create and run the agent
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

        # Run the agent to generate testable unit scenarios for this unit
        try:
            final_response = ""
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
                        print(
                            f"Received response from the agent for unit: {testable_unit['id']}"
                        )

            # Step 1: Try to parse the entire response as JSON
            try:
                parsed_json = json.loads(final_response)
                # Add the unit ID to the scenario
                all_scenarios["testableUnitScenarios"].append(parsed_json)

            # Step 2: If that fails, try to find JSON code blocks
            except json.JSONDecodeError:
                print("Response is not valid JSON, looking for code blocks...")
                json_blocks_found = False

                # Look for code blocks
                for match in re.finditer(
                    r"```(?:json)?\n(.*?)\n```", final_response, re.DOTALL
                ):
                    json_content = match.group(1).strip()
                    try:
                        parsed_json = json.loads(json_content)
                        # Add the unit ID to the scenario
                        scenario = {
                            "id": f"SCENARIO-{testable_unit['id']}-block",
                            "testableUnitId": testable_unit["id"],
                            "unitName": testable_unit["name"],
                            "name": testable_unit["name"],
                            "description": parsed_json.get("description", ""),
                            "data": parsed_json,
                        }
                        all_scenarios["testableUnitScenarios"].append(scenario)
                        json_blocks_found = True
                        break
                    except json.JSONDecodeError:
                        continue

                # Step 3: If no JSON found, add a placeholder
                if not json_blocks_found:
                    scenario = {
                        "id": f"PLACEHOLDER-{testable_unit['id']}",
                        "testableUnitId": testable_unit["id"],
                        "unitName": testable_unit["name"],
                        "name": testable_unit["name"],
                        "description": "Could not parse response as JSON",
                    }
                    all_scenarios["testableUnitScenarios"].append(scenario)

        except Exception as e:
            print(f"Error processing unit {testable_unit['id']}: {str(e)}")
            # Add error scenario
            error_scenario = {
                "id": f"ERROR-{testable_unit['id']}",
                "testableUnitId": testable_unit["id"],
                "unitName": testable_unit["name"],
                "name": f"Error processing {testable_unit['name']}",
                "description": f"Error: {str(e)}",
            }
            all_scenarios["testableUnitScenarios"].append(error_scenario)

    # Save all scenarios to file
    scenarios_file_path = os.path.join(
        project_path, "analysis", procedure, "testable_unit_scenarios.json"
    )
    with open(scenarios_file_path, "w") as f:
        json.dump(all_scenarios, f, indent=2)

    print(
        f"Created testable unit scenarios file with {len(all_scenarios['testableUnitScenarios'])} scenarios at {scenarios_file_path}"
    )
    return True


def run_testable_unit_scenarios(procedure_name, project_path):
    """CLI menu function to select and analyze procedures"""
    print("=== Testable Unit Scenarios Builder ===")

    # Get all procedures
    procedures = get_procedures(project_path)

    testable_unit_scenarios(procedure_name, project_path)
