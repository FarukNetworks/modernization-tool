import os
import sys
import json
import uuid
import re
import traceback

# Add parent directory to path to ensure imports work
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from app.agents.csharp_test_generation_agent.prompt import get_prompt
from app.agents.csharp_test_generation_agent.agent import root_agent


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


def save_test_file(project_path, procedure, scenario_id, code):
    """Save a C# test file to the correct location"""
    # Create test directory path
    test_dir = os.path.join(project_path, "csharp-code", "Tests", procedure)
    os.makedirs(test_dir, exist_ok=True)

    # Generate test file name
    file_name = f"{procedure}_{scenario_id}.cs"
    file_path = os.path.join(test_dir, file_name)

    try:
        # Save the file
        with open(file_path, "w") as f:
            f.write(code)
        print(f"  ✅ Created test file: {file_name}")
        return True
    except Exception as e:
        print(f"  ❌ Error creating test file {file_name}: {str(e)}")
        error_log_path = os.path.join(test_dir, "error_files.txt")
        with open(error_log_path, "a") as error_log:
            error_log.write(f"Error with file {file_name}: {str(e)}\n")
            error_log.write(f"Content:\n{code}\n\n")
            error_log.write("-" * 80 + "\n\n")
        return False


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


def extract_csharp_code(response_text):
    """Extract C# code from the model response"""
    # Extract code from response
    code_pattern = r"```csharp\s*(.*?)```"
    matches = re.findall(code_pattern, response_text, re.DOTALL)

    if matches:
        # Get the longest C# code block (most likely the complete test)
        return max(matches, key=len).strip()

    # Try without language marker
    code_pattern = r"```\s*(.*?)```"
    matches = re.findall(code_pattern, response_text, re.DOTALL)

    if matches:
        return max(matches, key=len).strip()

    # If no code blocks found, return the entire response
    return response_text


def generate_csharp_test(procedure, project_path):
    """Generate C# tests for a procedure"""
    print(f"\nGenerating C# tests for {procedure}...")

    # Get integration test spec
    test_spec = get_integration_test_spec(procedure, project_path)
    if not test_spec:
        print(f"No test specifications found for {procedure}")
        return False

    # Extract test scenarios
    test_scenarios = test_spec.get("testScenarios", [])
    if not test_scenarios:
        test_scenarios = test_spec.get("scenarios", [])
    if not test_scenarios and isinstance(test_spec, list):
        test_scenarios = test_spec

    if not test_scenarios:
        print(f"No test scenarios found in specifications for {procedure}")
        return False

    # Create the session service
    session_service = InMemorySessionService()

    # Create the agent runner
    runner = Runner(
        agent=root_agent,
        app_name="csharp_test_generation_agent",
        session_service=session_service,
    )

    total_count = len(test_scenarios)
    success_count = 0

    # Process each test scenario
    for i, scenario in enumerate(test_scenarios):
        # Extract scenario ID and description
        scenario_id = scenario.get("testId", scenario.get("id", f"test{i+1}"))
        description = scenario.get("description", "No description")

        print(
            f"  Generating test for scenario {scenario_id}: {description} ({i+1}/{total_count})"
        )

        try:
            # Create session
            session_id = f"csharp_test_{procedure}_{scenario_id}"
            session_service.create_session(
                app_name="csharp_test_generation_agent",
                user_id="user",
                session_id=session_id,
            )

            # Create prompt and run the agent
            prompt_text = get_prompt(procedure, project_path, scenario)

            # The prompt_text is already a Content object, so use it directly
            # instead of creating a new one

            # Get the response
            response_text = None
            for event in runner.run(
                user_id="user",
                session_id=session_id,
                new_message=prompt_text,
            ):
                if hasattr(event, "is_final_response") and event.is_final_response():
                    if event.content and event.content.parts:
                        response_text = event.content.parts[0].text
                        print(f"  Received response for scenario {scenario_id}")

            # If we got a response, process it
            if response_text:
                # Extract C# code from the response
                code = extract_csharp_code(response_text)

                # Save the file
                if save_test_file(project_path, procedure, scenario_id, code):
                    success_count += 1
            else:
                print(f"  ❌ No response received for scenario {scenario_id}")

        except Exception as e:
            print(f"  ❌ Error generating test for scenario {scenario_id}: {str(e)}")
            traceback.print_exc()

    # Show summary
    print(
        f"\n✅ Created {success_count} of {total_count} C# test files for {procedure}"
    )
    return success_count > 0


def run_csharp_test_generation(project_path):
    """Run C# test generation for all procedures"""
    print("Starting C# test generation...")
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
            input("\nSelect a procedure to generate C# tests for (enter number): ")
        )

        if 1 <= choice <= len(procedures):
            # Generate tests for a single procedure
            procedure = procedures[choice - 1]
            return generate_csharp_test(procedure, project_path)

        elif choice == len(procedures) + 1:
            # Generate tests for all procedures
            success_count = 0
            for i, procedure in enumerate(procedures):
                print(f"\nProcessing {procedure} ({i+1}/{len(procedures)})...")
                if generate_csharp_test(procedure, project_path):
                    success_count += 1

            print(
                f"\nC# test generation completed for {success_count} of {len(procedures)} procedures."
            )
            return success_count > 0

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


def generate_csharp_tests_cli(project_path):
    """
    Simple function to be called from the CLI that handles the entire process
    of generating C# tests for a project.
    """
    print("Generating C# tests for project...")

    procedures = get_procedures(project_path)
    if not procedures:
        print("No procedures found in the project")
        return False

    print(f"Found {len(procedures)} procedures")

    choices = ["Show full menu"] + procedures + ["Return to main menu"]

    # Import inquirer here to avoid potential circular imports
    import inquirer

    questions = [
        inquirer.List(
            "csharp_test_choice",
            message="Which procedure would you like to generate C# tests for?",
            choices=choices,
        ),
    ]

    selected = inquirer.prompt(questions)["csharp_test_choice"]

    if selected == "Show full menu":
        return run_csharp_test_generation(project_path)
    elif selected == "Return to main menu":
        return True
    else:
        return generate_csharp_test(selected, project_path)
