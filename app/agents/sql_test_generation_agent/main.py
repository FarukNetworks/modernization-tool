import os
import sys
import json
import re
import traceback

# Add parent directory to path to ensure imports work
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from app.agents.sql_test_generation_agent.prompt import get_prompt
from app.agents.sql_test_generation_agent.agent import root_agent
from app.shared.get_dependencies import get_dependencies


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


def create_sql_test_directory(procedure, project_path):
    """Create SQL test directory for the selected procedure"""
    sql_test_dir = os.path.join(project_path, "sql_tests", procedure)
    os.makedirs(sql_test_dir, exist_ok=True)
    return sql_test_dir


def save_sql_file(file_path, content):
    """Save the file content to the specified path"""
    # Create the full directory path
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save the file content
    with open(file_path, "w") as f:
        f.write(content)


def generate_test_class_template(procedure):
    """Generate a test class template for a procedure"""
    return f"""-- Auto-generated tSQLt test class for {procedure}
EXEC tSQLt.NewTestClass 'test_{procedure}';
GO
"""


def get_integration_test_spec(procedure, project_path):
    """Find and load the integration test specification file for a procedure"""
    # Look in the analysis directory first
    spec_path = os.path.join(
        project_path, "analysis", procedure, f"{procedure}_integration_test_specs.json"
    )
    if not os.path.exists(spec_path):
        spec_path = os.path.join(
            project_path,
            "analysis",
            procedure,
            f"{procedure}_integration_test_spec.json",
        )

    if os.path.exists(spec_path):
        try:
            with open(spec_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {spec_path}: {str(e)}")

    print(f"Integration test spec not found for {procedure}")
    return None


def generate_sql_test(procedure, project_path):
    """Generate SQL tests for a procedure"""
    print(f"\nGenerating SQL tests for {procedure}...")

    # Create test directory and file paths
    sql_test_dir = create_sql_test_directory(procedure, project_path)
    test_file_path = os.path.join(sql_test_dir, f"{procedure}_test.sql")

    # Get the procedure definition
    procedure_file = os.path.join(
        project_path, "sql_raw", procedure, f"{procedure}.sql"
    )
    if not os.path.exists(procedure_file):
        print(f"Procedure file not found at {procedure_file}")
        return False

    try:
        with open(procedure_file, "r") as f:
            procedure_definition = f.read()
    except Exception as e:
        print(f"Error reading procedure file: {str(e)}")
        return False

    # Get integration test spec
    test_spec = get_integration_test_spec(procedure, project_path)
    if not test_spec:
        return False

    # Extract test scenarios
    test_scenarios = test_spec.get("testScenarios", [])
    if not test_scenarios:
        test_scenarios = test_spec.get("scenarios", [])
    if not test_scenarios and isinstance(test_spec, list):
        test_scenarios = test_spec

    if not test_scenarios:
        print(f"No test scenarios found for {procedure}")
        return False

    # Initialize test content with class template - only add the NewTestClass once at the top
    test_content = generate_test_class_template(procedure)

    # Setup session service and runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="sql_test_generation_agent",
        session_service=session_service,
    )

    # Process each test scenario
    processed_count = 0
    for scenario in test_scenarios:
        scenario_id = scenario.get("testId", "unknown")
        description = scenario.get("description", "")

        print(f"  Generating test for scenario {scenario_id}: {description}")

        try:
            # Create session
            session_id = f"sql_test_{procedure}_{scenario_id}"
            session = session_service.create_session(
                app_name="sql_test_generation_agent",
                user_id="user",
                session_id=session_id,
            )

            # Create prompt and content object
            prompt_text = get_prompt(
                procedure, procedure_definition, project_path, scenario
            )
            content = types.Content(role="user", parts=[types.Part(text=prompt_text)])

            # Run the agent
            final_response = None
            for event in runner.run(
                user_id="user",
                session_id=session_id,
                new_message=content,
            ):
                if hasattr(event, "is_final_response") and event.is_final_response():
                    if event.content and event.content.parts:
                        final_response = event.content.parts[0].text
                        print(f"  Received response for scenario {scenario_id}")

            # Process response
            if final_response:
                # Clean up any markdown formatting
                test_case = (
                    final_response.replace("```sql", "").replace("```", "").strip()
                )

                # Remove any NewTestClass statements from the individual test cases
                test_case = re.sub(
                    r'EXEC\s+tSQLt\.NewTestClass\s+[\'"]test_\w+[\'"]\s*;?\s*GO\s*',
                    "",
                    test_case,
                    flags=re.IGNORECASE | re.MULTILINE,
                )

                # Ensure test procedure name is correct
                pattern = rf"\[test_{procedure}\]\.\[test_{procedure}_{scenario_id}\]"
                if not re.search(pattern, test_case):
                    test_case = re.sub(
                        r"CREATE PROCEDURE\s+\[\w+\.\w+\]\.\[[^\]]+\]",
                        f"CREATE PROCEDURE [test_{procedure}].[test_{procedure}_{scenario_id}]",
                        test_case,
                    )

                # Ensure proper GO statement at the end
                if not test_case.endswith("GO"):
                    if test_case.endswith("END;"):
                        test_case += "\nGO"
                    else:
                        test_case += "\nEND;\nGO"

                # Add test case to overall content
                test_content += (
                    f"\n\n-- Test scenario: {scenario_id} - {description}\n\n"
                )
                test_content += test_case
                processed_count += 1
                print(f"  ✓ Test generated for scenario {scenario_id}")
            else:
                print(f"  ✗ No response received for scenario {scenario_id}")

        except Exception as e:
            print(f"  ✗ Error generating test for scenario {scenario_id}: {str(e)}")
            traceback.print_exc()

    # Save the complete test file if any tests were generated
    if processed_count > 0:
        save_sql_file(test_file_path, test_content)
        print(f"SQL tests for {procedure} saved to {test_file_path}")
        print(
            f"You can now run the tests by selecting 'Run SQL Tests' from the main menu."
        )
        return True
    else:
        print(f"No tests were generated for {procedure}")
        return False


def run_sql_test_generation(project_path):
    """Run SQL test generation for all procedures"""
    procedures = get_procedures(project_path)

    if not procedures:
        print("No procedures found in the project")
        return False

    print(f"Found {len(procedures)} procedures")

    # Display menu
    print("\nAvailable procedures:")
    for i, proc in enumerate(procedures):
        print(f"{i+1}. {proc}")
    print(f"{len(procedures)+1}. Generate tests for all procedures")
    print(f"{len(procedures)+2}. Return to main menu")

    # Get user selection
    try:
        choice = int(
            input("\nSelect a procedure to generate SQL tests for (enter number): ")
        )

        if 1 <= choice <= len(procedures):
            # Generate tests for a single procedure
            procedure = procedures[choice - 1]
            generate_sql_test(procedure, project_path)
            return True

        elif choice == len(procedures) + 1:
            # Generate tests for all procedures
            for i, procedure in enumerate(procedures):
                print(f"\nProcessing {procedure} ({i+1}/{len(procedures)})...")
                generate_sql_test(procedure, project_path)

            print(
                f"\nSQL test generation completed for all {len(procedures)} procedures."
            )
            return True

        elif choice == len(procedures) + 2:
            print("Returning to main menu...")
            return True

        else:
            print("Invalid choice. Please try again.")
            return False

    except ValueError:
        print("Please enter a valid number.")
        return False

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return False
