import os
import sys
import json
import uuid
import re
import glob
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.agents.implementation_executor_agent.prompt import get_prompt
from app.agents.implementation_executor_agent.agent import root_agent
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


def extract_files_from_response(result, project_path):
    """Extract C# files from the model response and save them to csharp-code directory"""
    # Extract file names and codes
    file_paths = []
    file_contents = []

    # Extract file paths and contents - FIXED REGEX PATTERN
    pattern = r"FILE:\s*([\w./\\-]+)\s*```(?:csharp|json|xml)\s*(.*?)```"
    for match in re.finditer(pattern, result, re.DOTALL):
        file_path = match.group(1).strip()
        file_content = match.group(2).strip()

        # Skip empty paths or contents
        if not file_path or not file_content:
            continue

        file_paths.append(file_path)
        file_contents.append(file_content)

    # Create csharp-code directory
    csharp_dir = os.path.join(project_path, "csharp-code")
    os.makedirs(csharp_dir, exist_ok=True)

    created_files = []

    # Create each file in the appropriate directory
    for file_path, file_content in zip(file_paths, file_contents):
        try:
            # Clean the file path (remove any unexpected characters)
            clean_path = file_path.strip()

            # Create the full directory path
            full_dir = os.path.join(csharp_dir, os.path.dirname(clean_path))
            os.makedirs(full_dir, exist_ok=True)

            # Save the file content
            full_path = os.path.join(csharp_dir, clean_path)

            # Check if path is too long
            if len(full_path) > 255:  # Maximum path length on most systems
                print(f"⚠️ Path too long, truncating: {clean_path}")
                # Truncate the filename if needed
                base_dir = os.path.dirname(full_path)
                filename = os.path.basename(clean_path)
                if len(filename) > 50:
                    filename = filename[:45] + "..." + filename[-5:]
                full_path = os.path.join(base_dir, filename)

            with open(full_path, "w") as f:
                f.write(file_content)

            created_files.append(clean_path)
            print(f"✅ Created file: {clean_path}")

        except Exception as e:
            print(f"❌ Error creating file {file_path}: {str(e)}")
            # Save to an error log file instead
            error_log_path = os.path.join(csharp_dir, "error_files.txt")
            with open(error_log_path, "a") as error_log:
                error_log.write(f"Error with file {file_path}: {str(e)}\n")
                error_log.write(f"Content:\n{file_content}\n\n")
                error_log.write("-" * 80 + "\n\n")

    return created_files


def implementation_executor(procedure, project_path):
    """Main entry point - execute implementation for a procedure based on its analysis"""
    print(f"\nStarting implementation execution for {procedure}")

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

    APP_NAME = "Stored Procedure Implementation Executor"
    USER_ID = "project_owner"
    SESSION_ID = str(uuid.uuid4())
    session = session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    print("Created new session")
    print(f"\tSession ID: {SESSION_ID}")

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

    # Run the agent to generate implementation executor
    print("Executing implementation...")
    try:
        for event in runner.run(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=get_prompt(procedure, procedure_definition, project_path),
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    print(f"Received response from the agent")

                    # Debug: Check if the response contains the expected file pattern
                    if "FILE:" in final_response and "```csharp" in final_response:
                        print("Response contains file markers")
                    else:
                        print(
                            "WARNING: Response does not contain expected file markers"
                        )
                        print("First 150 chars of response:", final_response[:150])

        # Extract and save files
        saved_files = extract_files_from_response(final_response, project_path)
        csharp_dir = os.path.join(project_path, "csharp-code")
        print(f"Created {len(saved_files)} implementation files in {csharp_dir}")
        return True

    except Exception as e:
        print(f"Error during implementation execution: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def run_implementation_executor(project_path):
    """CLI menu function to select and execute implementations for procedures"""
    print("=== Stored Procedure Implementation Executor ===")

    # Get all procedures
    procedures = get_procedures(project_path)

    if not procedures:
        print(f"No procedures found in {os.path.join(project_path, 'sql_raw')}")
        return

    # Display menu
    print("\nAvailable procedures:")
    for i, proc in enumerate(procedures):
        print(f"{i+1}. {proc}")
    print(f"{len(procedures)+1}. Execute all procedures")
    print(f"{len(procedures)+2}. Return to main menu")

    # Get user selection
    try:
        choice = int(input("\nSelect a procedure to execute (enter number): "))

        if 1 <= choice <= len(procedures):
            # Execute single procedure
            procedure = procedures[choice - 1]
            implementation_executor(procedure, project_path)
            return

        elif choice == len(procedures) + 1:
            # Execute all procedures
            completed = 0
            total = len(procedures)

            for procedure in procedures:
                print(f"\nProcessing {procedure} ({completed+1}/{total})...")
                implementation_executor(procedure, project_path)
                completed += 1

            print(
                f"\nImplementation execution completed for all {completed} procedures."
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
