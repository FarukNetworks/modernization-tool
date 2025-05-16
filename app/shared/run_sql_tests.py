import os
import json
import re
import time
import shutil
import pyodbc
import sqlparse
from datetime import datetime
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Global variable to track database connection
db_connection = None
db_cursor = None


def get_db_connection(connection_string):
    """Get a database connection with retry logic"""
    global db_connection, db_cursor

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            if db_connection is None or db_cursor is None:
                print("Establishing new database connection...")
                db_connection = pyodbc.connect(connection_string)
                db_cursor = db_connection.cursor()

            # Test the connection
            db_cursor.execute("SELECT 1")
            return db_connection, db_cursor

        except Exception as e:
            retry_count += 1
            print(f"Connection error (attempt {retry_count}/{max_retries}): {str(e)}")

            # Close any existing connection before retrying
            try:
                if db_cursor:
                    db_cursor.close()
                if db_connection:
                    db_connection.close()
            except:
                pass

            db_connection = None
            db_cursor = None

            if retry_count < max_retries:
                time.sleep(2)  # Wait before retrying
            else:
                raise Exception(
                    f"Failed to establish database connection after {max_retries} attempts"
                )


def upload_batch_json(
    project_path,
    index,
    batch,
    procedure,
    scenario_id,
    status="Uploaded",
    error_message="",
):
    """Save batch upload results to JSON"""
    results_dir = os.path.join(project_path, "sql_tests", procedure, "results")
    os.makedirs(results_dir, exist_ok=True)

    upload_data = {
        "index": index,
        "batch": batch,
        "test_results": status,
        "test_name": f"[test_{procedure}].[test_{procedure}_{scenario_id}]",
        "timestamp": datetime.now().isoformat(),
        "Msg": (
            error_message if isinstance(error_message, str) else str(error_message)
        ),  # Convert to string
    }

    with open(
        os.path.join(results_dir, f"batch_{index}_upload_results.json"), "w"
    ) as f:
        json.dump(upload_data, f, indent=4)


def extract_batch_info(batch, procedure):
    """Extract scenario ID and type from batch"""
    # Default values
    scenario_id = "default"
    batch_type = "unknown"

    # Extract scenario ID from procedure name pattern
    proc_match = re.search(
        rf"\[test_{procedure}\]\.\[test_{procedure}_([^\]]+)\]", batch
    )
    if proc_match:
        scenario_id = proc_match.group(1)

    # Determine batch type
    if "CREATE PROCEDURE" in batch:
        batch_type = "procedure_creation"
    elif "EXEC tSQLt.NewTestClass" in batch:
        batch_type = "test_class_creation"
    elif "INSERT INTO" in batch or "UPDATE" in batch or "DELETE" in batch:
        batch_type = "data_manipulation"

    return scenario_id, batch_type


def extract_test_name(batch):
    """
    Extract test name from a SQL batch containing CREATE PROCEDURE.

    Args:
        batch (str): SQL batch content

    Returns:
        str: Full test name with brackets or None if not found
    """
    try:
        for line in batch.splitlines():
            if "CREATE PROCEDURE" in line:
                # Extract the full procedure name with brackets
                match = re.search(r"CREATE PROCEDURE (\[.*?\]\.\[.*?\])", line)
                if match:
                    return match.group(1)
    except Exception as e:
        print(f"❌ Failed to extract test name from batch: {e}")

    return None


def execute_tsqlt_test(cursor, connection, test_name):
    """
    Execute a tSQLt test and capture all returned result sets.

    Args:
        cursor: Database cursor
        connection: Database connection
        test_name (str): Name of the test to run

    Returns:
        tuple: (test_results, test_result_data, messages, error_message, results)
    """
    test_results = []  # Will store structured data for detailed logging
    test_result_data = []  # Will store tSQLt.TestResult data
    messages = []  # Will store SQL Server messages
    error_message = None  # Will store any error message
    raw_results = []  # Will store the raw result sets for the final JSON

    try:
        print(f"🧪 Executing tSQLt.Run for test: {test_name}")

        # Clear the test result table
        cursor.execute("DELETE FROM tSQLt.TestResult")

        # Execute the test
        sql_command = f"EXEC tSQLt.Run '{test_name}'"
        cursor.execute(sql_command)

        # Capture all result sets
        result_set_index = 0
        while True:
            if cursor.description:
                print(f"📊 Processing result set #{result_set_index}")
                columns = [column[0] for column in cursor.description]
                print(
                    f"   Columns ({len(columns)}): {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}"
                )

                rows = cursor.fetchall()
                print(f"   Rows: {len(rows)}")

                if rows:
                    # Create a list of dictionaries for this result set
                    result_data = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            # Convert datetime objects to strings
                            if isinstance(value, datetime):
                                row_dict[col] = value.isoformat()
                            else:
                                row_dict[col] = value
                        result_data.append(row_dict)

                    # Store in test_results for structured logging
                    test_results.append(
                        {
                            "result_set": result_set_index,
                            "columns": columns,
                            "row_count": len(rows),
                            "data": result_data,
                        }
                    )

                    # Store the raw data for the JSON output
                    raw_results.append(result_data)

                    print(
                        f"   ✅ Added result set #{result_set_index} to results ({len(rows)} rows)"
                    )

            # Capture SQL Server messages
            for message in cursor.messages:
                if message and len(message) > 1:
                    messages.append(message[1])

            # Move to next result set
            if not cursor.nextset():
                print("⛔ No more result sets")
                break

            result_set_index += 1

        print(f"📊 Captured {len(test_results)} total result sets from test execution")

        # Get tSQLt.TestResult data
        try:
            cursor.execute(f"SELECT * FROM [tSQLt].[TestResult]")
            test_result_rows = cursor.fetchall()
            if test_result_rows:
                columns = [column[0] for column in cursor.description]
                test_result_data = [dict(zip(columns, row)) for row in test_result_rows]

                # Convert datetime objects to strings
                for row in test_result_data:
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            row[key] = value.isoformat()

                print(f"✅ Found {len(test_result_data)} rows in tSQLt.TestResult")
            else:
                print("ℹ️ No rows found in tSQLt.TestResult")
        except Exception as e:
            print(f"⚠️ Error fetching tSQLt.TestResult: {str(e)}")

    except Exception as e:
        error_message = str(e)
        print(f"❌ Error executing test {test_name}: {error_message}")

        # Try to get tSQLt.TestResult even after error
        try:
            cursor.execute(
                f"SELECT * FROM [tSQLt].[TestResult] WHERE Name LIKE '%{test_name}%'"
            )
            test_result_rows = cursor.fetchall()
            if test_result_rows and cursor.description:
                columns = [column[0] for column in cursor.description]
                test_result_data = [dict(zip(columns, row)) for row in test_result_rows]

                # Convert datetime objects to strings
                for row in test_result_data:
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            row[key] = value.isoformat()
        except Exception as inner_e:
            print(
                f"❌ Could not retrieve tSQLt results after test failure: {str(inner_e)}"
            )

    # Print summary of captured data
    print(f"\n📋 EXECUTION SUMMARY:")
    print(f"   Result sets captured: {len(test_results)}")
    print(f"   Raw result sets for JSON: {len(raw_results)}")
    print(f"   tSQLt.TestResult rows: {len(test_result_data)}")
    print(f"   Messages captured: {len(messages)}")
    print(f"   Error: {'None' if error_message is None else error_message}")

    return (
        test_results,
        test_result_data,
        messages,
        error_message,
        raw_results,
    )


def save_test_results(
    project_path,
    procedure,
    test_name,
    test_results,
    test_result_data,
    messages,
    error_message=None,
    results=None,
):
    """
    Save test execution results to files.

    Args:
        project_path (str): Project path
        procedure (str): Procedure name
        test_name (str): Test name
        test_results (list): List of structured result data sets
        test_result_data (list): tSQLt.TestResult data
        messages (list): Execution messages
        error_message (str, optional): Error message if test failed
        results (list, optional): Raw result sets from tSQLt.Run for JSON output
    """
    # Create results directory
    results_dir = os.path.join(project_path, "sql_tests", procedure, "results")
    os.makedirs(results_dir, exist_ok=True)

    # Generate safe filename from test name
    safe_filename = test_name.replace("[", "").replace("]", "").replace(".", "_")

    # Save tSQLt.TestResult data with result sets
    if test_result_data:
        # Create the final JSON structure
        result_data = {
            "tsqlt_results": test_result_data,
            "results": results if results else [],
        }
        with open(f"{results_dir}/{safe_filename}_tsqlt_results.json", "w") as f:
            json.dump(result_data, f, indent=4, default=str)
        print(f"📄 tSQLt.TestResult and result data saved for {test_name}")

    # Save error information if available
    if error_message:
        with open(f"{results_dir}/{safe_filename}_error.json", "w") as f:
            json.dump({"error": messages}, f, indent=4)
        print(f"📄 Error information saved for {test_name}")


def process_test_batch(batch, index, cursor, connection, procedure, project_path):
    """
    Process a SQL batch, executing it and running the test if it's a procedure.

    Args:
        batch (str): SQL batch content
        index (int): Batch index
        cursor: Database cursor
        connection: Database connection
        procedure (str): Procedure name being tested
        project_path (str): Project path

    Returns:
        bool: Success status
    """
    scenario_id, batch_type = extract_batch_info(batch, procedure)

    print(f"🔄 Processing batch {index} ({batch_type}) for {procedure}_{scenario_id}")

    try:
        # Execute the batch
        clean_batch = sqlparse.format(batch, strip_comments=True).strip()

        # Get test name from the batch
        test_name = extract_test_name(batch)

        # Drop the test before uploading
        if test_name:
            cursor.execute(f"DROP PROCEDURE IF EXISTS {test_name}")
            cursor.commit()

        cursor.execute(clean_batch)

        # Record successful upload
        upload_batch_json(
            project_path, index, batch, procedure, scenario_id, "Uploaded"
        )
        print(f"✅ Successfully uploaded batch {index} for {procedure}")

        # If it's a procedure creation, run the test
        if batch_type == "procedure_creation":
            test_name = extract_test_name(batch)
            if test_name:
                print(f"🧪 Running test: {test_name}")

                # Execute the test
                (
                    test_results,
                    test_result_data,
                    messages,
                    error_message,
                    results,
                ) = execute_tsqlt_test(cursor, connection, test_name)

                print("---------START OF ERROR MESSAGE-----------------------")
                print(messages)
                print("---------END OF ERROR MESSAGE-----------------------")

                # Save results regardless of success/failure
                save_test_results(
                    project_path,
                    procedure,
                    test_name,
                    test_results,
                    test_result_data,
                    messages,
                    error_message,
                    results,
                )

        # Non-procedure batches executed successfully
        return True

    except Exception as batch_error:
        error_message = str(batch_error)
        print(f"⚠️ Error in batch {index} ({procedure}_{scenario_id}): {error_message}")

        # Record failed upload
        upload_batch_json(
            project_path, index, batch, procedure, scenario_id, "Failed", batch_error
        )
        print(f"❌ Failed to process batch {index}")
        return False


def upload_batch(batch, index, procedure, scenario_id, connection_string, project_path):
    """Upload SQL batch with error handling and test execution

    Args:
        batch (str): SQL batch content to upload
        index (int): Batch index
        procedure (str): Procedure name being tested
        scenario_id (str): Test scenario ID
        connection_string (str): Database connection string
        project_path (str): Project path

    Returns:
        bool: Success status
    """
    connection, cursor = get_db_connection(connection_string)

    # Process the batch with the helper function
    return process_test_batch(batch, index, cursor, connection, procedure, project_path)


def naive_linechunk(sql_script):
    """Split SQL script into GO-separated batches with improved handling"""
    batches = []
    current_batch = []

    for line in sql_script.splitlines():
        stripped_line = line.strip()
        if stripped_line.upper() == "GO":
            batches.append("\n".join(current_batch))
            current_batch = []
        else:
            current_batch.append(line)

    if current_batch:
        batches.append("\n".join(current_batch))

    return [batch.strip() for batch in batches if batch.strip()]


def generate_global_summary(procedures, project_path):
    """
    Generate a global summary of test results across all procedures.

    Args:
        procedures (list): List of procedure names
        project_path (str): Project path

    Returns:
        dict: Summary data
    """
    global_summary = {
        "timestamp": datetime.now().isoformat(),
        "procedures_count": len(procedures),
        "procedures": {},
        "upload_summary": {"total": 0, "success": 0, "fixed": 0, "failed": 0},
        "test_summary": {
            "tsqlt": {"total": 0, "passed": 0, "failed": 0, "errored": 0},
        },
    }

    # Process each procedure
    for procedure in procedures:
        procedure_summary = {"name": procedure}
        results_dir = os.path.join(project_path, "sql_tests", procedure, "results")

        # Skip if no results directory
        if not os.path.exists(results_dir):
            procedure_summary["status"] = "No tests run"
            global_summary["procedures"][procedure] = procedure_summary
            continue

        # Look for all_tests_results.json file
        summary_file = os.path.join(results_dir, "all_tests_results.json")
        if os.path.exists(summary_file):
            try:
                with open(summary_file, "r") as f:
                    all_results = json.load(f)
                procedure_summary["all_results"] = all_results

                # Aggregate upload results
                if "upload_summary" in all_results:
                    global_summary["upload_summary"]["total"] += all_results[
                        "upload_summary"
                    ].get("total", 0)
                    global_summary["upload_summary"]["success"] += all_results[
                        "upload_summary"
                    ].get("success", 0)
                    global_summary["upload_summary"]["fixed"] += all_results[
                        "upload_summary"
                    ].get("fixed", 0)
                    global_summary["upload_summary"]["failed"] += all_results[
                        "upload_summary"
                    ].get("failed", 0)

                # Aggregate test results
                if "test_summary" in all_results:
                    global_summary["test_summary"]["tsqlt"]["total"] += all_results[
                        "test_summary"
                    ].get("total", 0)
                    global_summary["test_summary"]["tsqlt"]["passed"] += all_results[
                        "test_summary"
                    ].get("passed", 0)
                    global_summary["test_summary"]["tsqlt"]["failed"] += all_results[
                        "test_summary"
                    ].get("failed", 0)
                    global_summary["test_summary"]["tsqlt"]["errored"] += all_results[
                        "test_summary"
                    ].get("errored", 0)

            except Exception as e:
                procedure_summary["status"] = (
                    f"Error reading all_tests_results: {str(e)}"
                )

        else:
            # If all_tests_results.json doesn't exist, count batch uploads directly
            batch_count = {"success": 0, "fixed": 0, "failed": 0}
            for filename in os.listdir(results_dir):
                if filename.startswith("batch_") and filename.endswith(
                    "_upload_results.json"
                ):
                    try:
                        with open(os.path.join(results_dir, filename), "r") as f:
                            batch_data = json.load(f)
                            status = batch_data.get("test_results", "").lower()
                            if status == "uploaded":
                                batch_count["success"] += 1
                            elif status == "ai-fixed":
                                batch_count["fixed"] += 1
                            else:
                                batch_count["failed"] += 1
                    except:
                        batch_count["failed"] += 1

            procedure_summary["upload_summary"] = batch_count
            total_batches = sum(batch_count.values())

            # Aggregate upload counts
            global_summary["upload_summary"]["total"] += total_batches
            global_summary["upload_summary"]["success"] += batch_count["success"]
            global_summary["upload_summary"]["fixed"] += batch_count["fixed"]
            global_summary["upload_summary"]["failed"] += batch_count["failed"]

        # Store procedure summary
        global_summary["procedures"][procedure] = procedure_summary

    # Save global summary
    summary_dir = os.path.join(project_path, "sql_tests")
    os.makedirs(summary_dir, exist_ok=True)

    with open(os.path.join(summary_dir, "global_summary.json"), "w") as f:
        json.dump(global_summary, f, indent=4)

    # Print global summary
    print("\n📊 GLOBAL TEST SUMMARY:")
    print(f"   Procedures: {global_summary['procedures_count']}")
    print(
        f"   Upload: {global_summary['upload_summary']['total']} total, "
        f"{global_summary['upload_summary']['success']} success, "
        f"{global_summary['upload_summary']['fixed']} fixed, "
        f"{global_summary['upload_summary']['failed']} failed"
    )
    print(
        f"   tSQLt Tests: {global_summary['test_summary']['tsqlt']['total']} total, "
        f"{global_summary['test_summary']['tsqlt']['passed']} passed, "
        f"{global_summary['test_summary']['tsqlt']['failed']} failed, "
        f"{global_summary['test_summary']['tsqlt']['errored']} errored"
    )

    return global_summary


def run_all_tests_for_procedure(cursor, connection, procedure, project_path):
    """
    Run all tests for a procedure and save results.

    Args:
        cursor: Database cursor
        connection: Database connection
        procedure (str): Procedure name
        project_path (str): Project path
    """
    print(f"🧪 Running all tests for {procedure}")

    # Create a comprehensive results object
    all_results = {
        "procedure": procedure,
        "timestamp": datetime.now().isoformat(),
        "upload_summary": {"total": 0, "success": 0, "fixed": 0, "failed": 0},
        "test_summary": {"total": 0, "passed": 0, "failed": 0, "errored": 0},
    }

    # First, collect all batch upload results
    results_dir = os.path.join(project_path, "sql_tests", procedure, "results")
    os.makedirs(results_dir, exist_ok=True)

    try:
        if os.path.exists(results_dir):
            # Get batch upload information
            for filename in os.listdir(results_dir):
                if filename.startswith("batch_") and filename.endswith(
                    "_upload_results.json"
                ):
                    try:
                        with open(os.path.join(results_dir, filename), "r") as f:
                            batch_data = json.load(f)
                            status = batch_data.get("test_results", "").lower()

                            # Count in summary
                            all_results["upload_summary"]["total"] += 1
                            if status == "uploaded":
                                all_results["upload_summary"]["success"] += 1
                            elif status == "ai-fixed":
                                all_results["upload_summary"]["fixed"] += 1
                            else:
                                all_results["upload_summary"]["failed"] += 1
                    except Exception as e:
                        print(
                            f"⚠️ Error processing batch result file {filename}: {str(e)}"
                        )

            # Use sets to track unique test names
            unique_tests = set()
            passed_tests = set()
            failed_tests = set()
            errored_tests = set()

            # Count test results from individual test result files
            for filename in os.listdir(results_dir):
                if filename.endswith("_tsqlt_results.json"):
                    try:
                        with open(os.path.join(results_dir, filename), "r") as f:
                            test_data = json.load(f)
                            tsqlt_results = test_data.get("tsqlt_results", [])

                            for result in tsqlt_results:
                                test_name = result.get("Name")
                                if test_name:
                                    unique_tests.add(test_name)

                                    if result.get("Result") == "Success":
                                        passed_tests.add(test_name)
                                    elif result.get("Result") == "Failure":
                                        failed_tests.add(test_name)
                                    else:
                                        errored_tests.add(test_name)
                    except Exception as e:
                        print(
                            f"⚠️ Error processing test result file {filename}: {str(e)}"
                        )

            # For each test name, determine its final status (prioritizing success)
            final_test_count = len(unique_tests)
            final_passed_count = len(passed_tests)
            final_failed_count = len(
                failed_tests - passed_tests
            )  # Tests that failed and weren't later fixed
            final_errored_count = len(
                errored_tests - passed_tests - failed_tests
            )  # Tests that errored and weren't later fixed or failed

            # Update summary with deduplicated counts
            all_results["test_summary"]["total"] = final_test_count
            all_results["test_summary"]["passed"] = final_passed_count
            all_results["test_summary"]["failed"] = final_failed_count
            all_results["test_summary"]["errored"] = final_errored_count

            # Save comprehensive test results
            with open(f"{results_dir}/all_tests_results.json", "w") as f:
                json.dump(all_results, f, indent=4, default=str)
            print(f"📄 All test results saved for {procedure}")

    except Exception as e:
        error_message = str(e)
        print(f"❌ Failed to process test results for {procedure}: {error_message}")

        # Save error information
        with open(f"{results_dir}/all_tests_error.json", "w") as f:
            json.dump({"error": error_message}, f, indent=4)
        print(f"📄 Error information saved for all tests")


def run_sql_tests(project_path, connection_string=None):
    """
    Run SQL tests for all procedures in the project.

    Args:
        project_path (str): Path to the project directory
        connection_string (str, optional): Database connection string. If None, will try to load from project config

    Returns:
        bool: Success status
    """
    print(f"\n🧪 Running SQL tests for project at: {project_path}")

    # Get connection string from project config if not provided
    if connection_string is None:
        config_file = os.path.join(project_path, "connection_string.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    connection_string = config.get("connection_string", "")
            except Exception as e:
                print(f"❌ Failed to load connection string from config: {str(e)}")
                return False

        if not connection_string:
            print("❌ No connection string provided or found in project config")
            return False

    # Get database connection
    try:
        connection, cursor = get_db_connection(connection_string)
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

    # Get all procedures with generated SQL tests
    sql_tests_dir = os.path.join(project_path, "sql_tests")
    if not os.path.exists(sql_tests_dir):
        print("❌ No SQL tests directory found in the project")
        return False

    procedures = [
        folder
        for folder in os.listdir(sql_tests_dir)
        if os.path.isdir(os.path.join(sql_tests_dir, folder))
    ]

    if not procedures:
        print("❌ No procedures with SQL tests found")
        return False

    print(f"📋 Found {len(procedures)} procedures with SQL tests")

    # Clean up all results directories before starting
    for procedure in procedures:
        results_dir = os.path.join(project_path, "sql_tests", procedure, "results")
        if os.path.exists(results_dir):
            shutil.rmtree(results_dir)
            print(f"🧹 Cleaned up results directory for {procedure}")

    # Process each procedure
    for procedure in procedures:
        print(f"\n🔄 Processing procedure: {procedure}")

        # Create test directory path
        test_dir = os.path.join(project_path, "sql_tests", procedure)
        test_file_path = os.path.join(test_dir, f"{procedure}_test.sql")
        results_dir = os.path.join(test_dir, "results")

        # Create fresh results directory
        os.makedirs(results_dir, exist_ok=True)

        if not os.path.exists(test_file_path):
            print(f"❌ Test file does not exist: {test_file_path}")
            continue

        # Get the test SQL file code
        with open(test_file_path, "r") as f:
            test_file_code = f.read()

        # Execute tests
        if not test_file_code:
            print(f"❌ Empty test file for {procedure}, skipping")
            continue

        batches = naive_linechunk(test_file_code)

        # Upload and execute batches
        successful_batches = 0
        failed_batches = 0

        for index, batch in enumerate(batches):
            scenario_id, batch_type = extract_batch_info(batch, procedure)

            if upload_batch(
                batch, index, procedure, scenario_id, connection_string, project_path
            ):
                successful_batches += 1
            else:
                failed_batches += 1

        # After processing all batches, run all tests for this procedure
        connection, cursor = get_db_connection(
            connection_string
        )  # Get fresh connection for all tests
        run_all_tests_for_procedure(cursor, connection, procedure, project_path)

        print(f"\n📊 Results for {procedure}:")
        print(f"   ✅ Successful batches: {successful_batches}")
        print(f"   ❌ Failed batches: {failed_batches}")

    # Generate global summary across all procedures
    generate_global_summary(procedures, project_path)

    # Clean up database connection
    if db_cursor:
        db_cursor.close()
    if db_connection:
        db_connection.close()

    print("✅ SQL tests completed for all procedures")
    return True
