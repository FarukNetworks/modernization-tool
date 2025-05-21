import os
import sys
import json
import uuid
import re
import glob
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.agents.integration_test_spec_agent.prompt import get_prompt
from app.agents.integration_test_spec_agent.agent import root_agent
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

    # Extract direct JSON from the response
    if (
        not file_paths
        and result.strip().startswith("{")
        and result.strip().endswith("}")
    ):
        try:
            # Try to parse the response as JSON
            json_content = json.loads(result.strip())
            # Save it as a JSON file
            full_path = os.path.join(analysis_dir, "integration_test_spec.json")
            with open(full_path, "w") as f:
                json.dump(json_content, f, indent=2)
            file_paths.append("integration_test_spec.json")
        except json.JSONDecodeError:
            print("Response is not valid JSON")

    return file_paths


def check_required_files(procedure, project_path):
    """Check if all required files for integration test specification exist"""
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


def create_integration_test_spec(procedure, project_path):
    """Main entry point - create integration test specifications for a procedure"""
    print(f"\nStarting integration test specification for {procedure}")

    # Check if all required files exist
    if not check_required_files(procedure, project_path):
        print(
            f"Integration test specification failed for {procedure} due to missing required files"
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

    APP_NAME = "Integration Test Specification"
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

    # Load all the node files - business rules, functions and processes
    business_rules_path = os.path.join(analysis_dir, f"{procedure}_business_rules.json")
    business_functions_path = os.path.join(
        analysis_dir, f"{procedure}_business_functions.json"
    )
    business_processes_path = os.path.join(
        analysis_dir, f"{procedure}_business_processes.json"
    )

    # Load all the nodes into variables
    business_rules = []
    business_functions = []
    business_processes = []

    # Load business rules
    try:
        with open(business_rules_path, "r") as f:
            business_rules = json.load(f).get("businessRules", [])
        print(f"Loaded {len(business_rules)} business rules")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading business rules: {str(e)}")

    # Load business functions
    try:
        with open(business_functions_path, "r") as f:
            business_functions = json.load(f).get("businessFunctions", [])
        print(f"Loaded {len(business_functions)} business functions")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading business functions: {str(e)}")

    # Load business processes
    try:
        with open(business_processes_path, "r") as f:
            business_processes = json.load(f).get("businessProcesses", [])
        print(f"Loaded {len(business_processes)} business processes")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading business processes: {str(e)}")

    # Combine all nodes from different sources
    all_nodes = []

    # Add business rules with source identifier
    for rule in business_rules:
        rule["_source"] = "BusinessRule"
        all_nodes.append(rule)

    # Add business functions with source identifier
    for function in business_functions:
        function["_source"] = "BusinessFunction"
        all_nodes.append(function)

    # Add business processes with source identifier
    for process in business_processes:
        process["_source"] = "BusinessProcess"
        all_nodes.append(process)

    print(f"Total of {len(all_nodes)} nodes to process")

    # Initialize a dictionary to hold all test scenarios
    integration_test_specs = {"testScenarios": []}

    # Process all nodes
    test_specs_created = 0

    # Loop through all nodes and create test specs
    for node in all_nodes:
        # Collect the final response
        final_response = ""

        # Run the agent to generate test specification
        print(f"Generating test specification for {node['id']} ({node['_source']})...")
        try:
            for event in runner.run(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=get_prompt(
                    procedure, procedure_definition, project_path, node
                ),
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response = event.content.parts[0].text
                        print(f"Received response from the agent for {node['id']}")

                        # Check if the response is valid
                        if "```json" in final_response or (
                            final_response.strip().startswith("{")
                            and final_response.strip().endswith("}")
                        ):
                            print(f"Response contains valid JSON data")
                        else:
                            print(
                                f"WARNING: Response does not contain expected JSON format"
                            )
                            print("First 150 chars of response:", final_response[:150])

            # Extract JSON content from the response
            json_content = None

            # Extract JSON from code blocks
            if "```json" in final_response:
                match = re.search(r"```json\s*(.*?)\s*```", final_response, re.DOTALL)
                if match:
                    try:
                        json_content = json.loads(match.group(1))
                        test_specs_created += 1
                        print(f"Parsed test specification for {node['id']}")
                    except json.JSONDecodeError:
                        print(f"Invalid JSON in response for {node['id']}")
            # Or try direct JSON response
            elif final_response.strip().startswith(
                "{"
            ) and final_response.strip().endswith("}"):
                try:
                    json_content = json.loads(final_response.strip())
                    test_specs_created += 1
                    print(f"Parsed test specification for {node['id']}")
                except json.JSONDecodeError:
                    print(f"Invalid JSON in response for {node['id']}")

            # Add test scenarios to the combined specs
            if json_content and "testScenarios" in json_content:
                # Add source info to each test scenario for traceability
                for scenario in json_content["testScenarios"]:
                    scenario["source"] = node["_source"]
                    integration_test_specs["testScenarios"].append(scenario)

        except Exception as e:
            print(f"Error generating test specification for {node['id']}: {str(e)}")
            import traceback

            traceback.print_exc()
            continue

    # Save the combined test specs to a single file
    if integration_test_specs["testScenarios"]:
        combined_specs_file = os.path.join(
            analysis_dir, f"{procedure}_integration_test_spec.json"
        )
        with open(combined_specs_file, "w") as f:
            json.dump(integration_test_specs, f, indent=2)
        print(
            f"Created combined test specifications with {len(integration_test_specs['testScenarios'])} test scenarios in {combined_specs_file}"
        )
    else:
        print("No test scenarios were generated")

    print(f"Processed {test_specs_created} nodes to create test specifications")
    return test_specs_created > 0


def run_integration_test_spec(project_path):
    """CLI menu function to select and create integration test specifications"""
    print("=== Integration Test Specification Generator ===")

    # Get all procedures
    procedures = get_procedures(project_path)

    if not procedures:
        print(f"No procedures found in {os.path.join(project_path, 'sql_raw')}")
        return

    # Display menu
    print("\nAvailable procedures:")
    for i, proc in enumerate(procedures):
        print(f"{i+1}. {proc}")
    print(f"{len(procedures)+1}. Create test specs for all procedures")
    print(f"{len(procedures)+2}. Return to main menu")

    # Get user selection
    try:
        choice = int(
            input("\nSelect a procedure for test specification (enter number): ")
        )

        if 1 <= choice <= len(procedures):
            # Create test specs for single procedure
            procedure = procedures[choice - 1]
            create_integration_test_spec(procedure, project_path)
            return

        elif choice == len(procedures) + 1:
            # Create test specs for all procedures
            completed = 0
            total = len(procedures)

            for procedure in procedures:
                print(f"\nProcessing {procedure} ({completed+1}/{total})...")
                if create_integration_test_spec(procedure, project_path):
                    completed += 1

            print(
                f"\nIntegration test specification completed for {completed} procedures."
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
