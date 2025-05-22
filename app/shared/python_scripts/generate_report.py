#!/usr/bin/env python3
"""
Stored Procedure Analysis Report Generator

This script generates a comprehensive report on a stored procedure,
including its business purpose, process diagram, business functions,
testable units, and source code.

Usage:
    python generate_report.py [path_to_config_file]

    Or call programmatically with:
    run_generate_report(procedure, project_path)

When called programmatically, the script will automatically locate the required files
based on the project structure.
"""

import os
import sys
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Import modules - comment these out when not needed for direct imports
try:
    from modules.data_loader import load_all_data
    from modules.diagram_generator import generate_process_diagram
    from modules.report_components import (
        extract_business_purpose,
        generate_testable_units_table,
    )
    from modules.html_converter import generate_html_report

    MODULES_AVAILABLE = True
except ImportError:
    logger.warning("Report modules not available, using built-in functions only")
    MODULES_AVAILABLE = False


def generate_process_steps_table(business_functions, process_steps):
    """
    Create a table of process steps with their associated business functions.

    Args:
        business_functions (dict): The business functions data
        process_steps (list): The steps from the business process

    Returns:
        str: Markdown table of process steps
    """

    table = """### Process Steps

| Step Details | Business Function Name | Business Function Description |
|--------------|------------------------|-------------------------------|
"""

    # Extract functions from different possible structures in business_functions
    functions = []
    if isinstance(business_functions, dict):
        if "businessFunctions" in business_functions:
            functions = business_functions["businessFunctions"]
        elif "functions" in business_functions:
            functions = business_functions["functions"]
        elif "function_list" in business_functions:
            functions = business_functions["function_list"]

    # Create a lookup map for business functions by ID
    function_map = {}
    for function in functions:
        if isinstance(function, dict) and "id" in function:
            function_map[function["id"]] = function

    # Generate table rows from process steps
    if process_steps:
        for step in process_steps:
            if isinstance(step, dict):
                step_id = step.get("id", "Unknown")
                step_type = step.get("type", "Unknown")

                # Get the referenced business function
                bf_id = step.get("businessFunctionRef", step.get("functionId", ""))
                bf_name = "Unknown"
                bf_desc = "Unknown"

                # Look up the business function details
                if bf_id in function_map:
                    bf = function_map[bf_id]
                    bf_name = bf.get("name", "Unknown")
                    bf_desc = bf.get("description", "No description provided")

                # Escape pipe characters to maintain table structure
                step_id = step_id.replace("|", "\\|")
                step_type = step_type.replace("|", "\\|")
                bf_id = bf_id.replace("|", "\\|")
                bf_name = bf_name.replace("|", "\\|")
                bf_desc = bf_desc.replace("|", "\\|")

                # Format the merged step details cell with bolded step ID and smaller text for type and BF ID
                step_details = f"**{step_id}**<br><small>Type: {step_type}<br>Function: {bf_id}</small>"

                # Add row to table
                table += f"| {step_details} | {bf_name} | {bf_desc} |\n"
    else:
        table += "| - | - | - | - | - |\n"

    return table


def load_json_file(file_path, default=None):
    """Load a JSON file or return default if file doesn't exist"""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        else:
            logger.warning(f"File not found: {file_path}")
            return default
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        return default


def load_sql_file(file_path):
    """Load a SQL file or return empty string if file doesn't exist"""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return f.read()
        else:
            logger.warning(f"SQL file not found: {file_path}")
            return ""
    except Exception as e:
        logger.error(f"Error loading SQL file {file_path}: {e}")
        return ""


def load_procedure_data(procedure, project_path):
    """Load all data for a procedure from the project structure"""
    # Define paths based on project structure
    # The SQL file is in sql_raw folder
    sql_file_path = f"{project_path}/sql_raw/{procedure}/{procedure}.sql"

    # Business function files - exact matches to the folder structure
    business_function_paths = [
        f"{project_path}/analysis/{procedure}/business_functions.json"
    ]

    # Business process files - note the plural "processes" in the filename
    business_process_paths = [
        f"{project_path}/analysis/{procedure}/business_processes.json"
    ]

    # Testable units are stored as a JSON file, not in a directory
    testable_units_paths = [
        f"{project_path}/analysis/{procedure}/testable_units.json",
        f"{project_path}/analysis/{procedure}/testable_unit_scenarios.json",
    ]

    # Additional files that might contain business purpose
    additional_files = [
        f"{project_path}/analysis/{procedure}/faq.json",
        f"{project_path}/analysis/{procedure}/implementation_approach.json",
        f"{project_path}/analysis/{procedure}/business_rules.json",
        f"{project_path}/analysis/{procedure}/specific_considerations.json",
    ]

    # Load SQL code
    sql_code = load_sql_file(sql_file_path)
    if not sql_code:
        # If the main SQL file isn't found, try a fallback location
        alternative_sql_path = f"{project_path}/sql_raw/{procedure}.sql"
        sql_code = load_sql_file(alternative_sql_path)

    # Load business functions
    business_functions = {}
    for path in business_function_paths:
        data = load_json_file(path, {})
        if data and len(data) > 0:
            logger.info(f"Loaded business functions from {path}")
            business_functions = data
            break

    # Load business process
    business_process = {}
    for path in business_process_paths:
        data = load_json_file(path, {})
        if data and len(data) > 0:
            logger.info(f"Loaded business process from {path}")
            business_process = data
            break

    # Load testable units from JSON files (not directories)
    testable_units = []
    testable_unit_map = {}

    # First try loading from testable_units.json
    for path in testable_units_paths:
        data = load_json_file(path, {})
        if data:
            logger.info(f"Loaded testable units from {path}")

            # Handle different possible data structures
            if isinstance(data, list):
                # If it's already a list of units
                testable_units = data
            elif "testableUnits" in data:
                # If it's an object with a testableUnits array
                testable_units = data["testableUnits"]
            elif "units" in data:
                # Another possible structure
                testable_units = data["units"]
            elif "scenarios" in data:
                # For testable_unit_scenarios.json
                scenarios = data["scenarios"]
                if isinstance(scenarios, list):
                    for scenario in scenarios:
                        if "testableUnits" in scenario:
                            testable_units.extend(scenario["testableUnits"])

            # Create a map for quick lookup
            for unit in testable_units:
                if isinstance(unit, dict) and "id" in unit:
                    testable_unit_map[unit["id"]] = unit

            if testable_units:
                break

    # Look for business purpose in various files
    business_purpose = ""

    # First look in business process file
    if business_process:
        if "businessPurpose" in business_process:
            business_purpose = business_process["businessPurpose"]
        elif (
            "businessProcesses" in business_process
            and business_process["businessProcesses"]
        ):
            first_process = business_process["businessProcesses"][0]
            if "businessPurpose" in first_process:
                business_purpose = first_process["businessPurpose"]

    # If not found, check additional files
    if not business_purpose:
        for path in additional_files:
            data = load_json_file(path, {})
            if data:
                if "businessPurpose" in data:
                    business_purpose = data["businessPurpose"]
                    logger.info(f"Found business purpose in {path}")
                    break
                elif "purpose" in data:
                    business_purpose = data["purpose"]
                    logger.info(f"Found purpose in {path}")
                    break

    # Define output path
    output_dir = f"{project_path}/analysis/{procedure}"
    os.makedirs(output_dir, exist_ok=True)
    output_file_path = f"{output_dir}/analysis_report.md"

    return (
        sql_code,
        business_functions,
        business_process,
        testable_units,
        testable_unit_map,
        output_file_path,
        ["md", "html"],
        business_purpose,
    )


def generate_report_from_paths(config_path):
    """
    Generate a report using paths from a configuration file.
    This is used when the script is run directly with a config file.
    """
    if MODULES_AVAILABLE:
        return load_all_data(config_path)
    else:
        logger.error(
            "Cannot load data from config file: required modules not available"
        )
        sys.exit(1)


def generate_report(config_path=None, procedure=None, project_path=None):
    """
    Generate a comprehensive stored procedure analysis report.

    Args:
        config_path (str, optional): Path to the configuration file
        procedure (str, optional): Name of the procedure
        project_path (str, optional): Path to the project

    Returns:
        tuple: (str, str, list, str) - (Complete markdown report, Output file path, Output formats, Procedure name)
    """
    # Load all the data - either from config or from project structure
    if procedure and project_path:
        logger.info(
            f"Generating report for procedure {procedure} in project {project_path}"
        )
        data = load_procedure_data(procedure, project_path)
    elif config_path:
        logger.info(f"Generating report using config file: {config_path}")
        if MODULES_AVAILABLE:
            data = load_all_data(config_path)
        else:
            logger.error(
                "Cannot load data from config file: required modules not available"
            )
            return None, None, None, None
    else:
        logger.error(
            "Either config_path or both procedure and project_path must be provided"
        )
        return None, None, None, None

    (
        sql_code,
        business_functions,
        business_process,
        testable_units,
        testable_unit_map,
        output_file_path,
        output_formats,
        business_purpose,
    ) = data

    # Extract the process steps
    process_steps = []
    if business_process and isinstance(business_process, dict):
        if (
            "businessProcesses" in business_process
            and isinstance(business_process["businessProcesses"], list)
            and business_process["businessProcesses"]
        ):
            first_process = business_process["businessProcesses"][0]
            if (
                isinstance(first_process, dict)
                and "orchestration" in first_process
                and "steps" in first_process["orchestration"]
            ):
                process_steps = first_process["orchestration"]["steps"]

    # Generate report sections
    process_diagram = ""
    if MODULES_AVAILABLE:
        process_diagram = generate_process_diagram(business_process, business_functions)
    else:
        process_diagram = (
            "*Process diagram generation requires the diagram_generator module*"
        )

    # Use our local function for process steps table
    functions_table = generate_process_steps_table(business_functions, process_steps)

    # Use the updated testable units display
    if MODULES_AVAILABLE:
        testable_units_table = generate_testable_units_table(testable_units)
    else:
        # Basic fallback for testable units
        testable_units_table = "| ID | Name | Description |\n|----|----|----|\n"
        for unit in testable_units:
            if isinstance(unit, dict):
                unit_id = unit.get("id", "Unknown")
                unit_name = unit.get("name", "Unknown")
                unit_desc = unit.get("description", "No description provided")
                testable_units_table += f"| {unit_id} | {unit_name} | {unit_desc} |\n"

    # Try to get procedure name from different sources
    procedure_name = None

    # If provided directly, use that
    if procedure:
        procedure_name = procedure

    # Otherwise try to extract from data
    if not procedure_name:
        # First try to get from businessProcesses array
        if (
            business_process
            and isinstance(business_process, dict)
            and "businessProcesses" in business_process
        ):
            if (
                isinstance(business_process["businessProcesses"], list)
                and business_process["businessProcesses"]
            ):
                procedure_name = business_process["businessProcesses"][0].get(
                    "name", None
                )

        # If not found, try other sources
        if not procedure_name:
            procedure_name = business_process.get("name", None)

        # If not found in business process, try to extract from SQL file
        if not procedure_name:
            # Try to extract from SQL file
            first_line = sql_code.split("\n")[0] if sql_code else ""
            if "PROCEDURE" in first_line or "procedure" in first_line.lower():
                # Extract procedure name from CREATE PROCEDURE statement
                proc_parts = first_line.split("PROCEDURE", 1)[-1].split("(")[0].strip()
                if proc_parts:
                    procedure_name = proc_parts

    # Fallback to default if still not found
    if not procedure_name:
        procedure_name = "Stored Procedure Analysis"

    # Add placeholder messages for empty sections
    if not business_purpose or business_purpose.strip() == "":
        business_purpose = "*(No business purpose information available. Run Business Analysis to generate this content.)*"

    if not process_steps or len(process_steps) == 0:
        process_steps_message = "*(No process steps information available. Run Business Analysis to generate this content.)*"
        functions_table += "\n" + process_steps_message

    if not testable_units or len(testable_units) == 0:
        testable_units_message = "*(No testable units information available. Run Testable Unit Scenarios to generate this content.)*"
        testable_units_table += "\n" + testable_units_message

    # Combine into markdown report
    report = f"""# {procedure_name} Analysis Report

## 1. Business Purpose
{business_purpose}

## 2. Key Business Process
{process_diagram}

{functions_table}

## 3. Testable Units Overview
{testable_units_table}

## 4. Stored Procedure Source Code
```sql
{sql_code}
```
"""

    return report, output_file_path, output_formats, procedure_name


def run_generate_report(procedure, project_path):
    """
    Main function to execute the report generation when called programmatically.

    Args:
        procedure (str): Name of the procedure
        project_path (str): Path to the project

    Returns:
        str: Path to the generated report file
    """
    logger.info(
        f"Generating report for procedure {procedure} in project {project_path}"
    )

    report, output_file_path, output_formats, procedure_name = generate_report(
        procedure=procedure, project_path=project_path
    )

    if not report or not output_file_path:
        logger.error("Failed to generate report data")
        return None

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file_path)
    os.makedirs(output_dir, exist_ok=True)

    # Check which output formats to generate
    formats = [f.strip().lower() for f in output_formats] if output_formats else ["md"]

    # Always generate markdown if needed
    if "md" in formats:
        try:
            with open(output_file_path, "w") as f:
                f.write(report)
            logger.info(f"Markdown report generated successfully at {output_file_path}")
        except Exception as e:
            logger.error(f"Error writing markdown report to file: {e}")
            return None

    # Generate HTML report if requested
    if "html" in formats and MODULES_AVAILABLE:
        try:
            # Derive HTML path from markdown path if needed
            html_path = (
                output_file_path.replace(".md", ".html")
                if output_file_path.endswith(".md")
                else output_file_path + ".html"
            )
            try:
                html_path = generate_html_report(
                    report, html_path, title=f"{procedure_name} - Interactive Report"
                )
                logger.info(f"HTML report generated successfully at {html_path}")
            except NameError:
                logger.warning(
                    "HTML report generation failed: generate_html_report function not available"
                )
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")

    return output_file_path


def generate_complete_analysis_report():
    """Main function to execute the report generation when run as a script"""

    # Default configuration file path
    default_config_path = "report_config.txt"

    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = default_config_path

    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}")
        print("Please provide a valid configuration file path.")
        print("Usage: python generate_report.py [path_to_config_file]")
        sys.exit(1)

    report, output_file_path, output_formats, procedure_name = generate_report(
        config_path=config_path
    )

    # Determine output path
    if not output_file_path:
        # Use a default output path
        output_dir = os.path.dirname(config_path)
        output_filename = "Stored_Procedure_Analysis_Report.md"
        output_path = os.path.join(output_dir, output_filename)
    else:
        output_path = output_file_path

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # Check which output formats to generate
    formats = [f.strip().lower() for f in output_formats] if output_formats else ["md"]

    # Always generate markdown if needed
    if "md" in formats:
        try:
            with open(output_path, "w") as f:
                f.write(report)
            print(f"Markdown report generated successfully at {output_path}")
        except Exception as e:
            print(f"Error writing markdown report to file: {e}")
            print("Displaying report content instead:")
            print("\n" + "=" * 80 + "\n")
            print(report)
            print("\n" + "=" * 80 + "\n")

    # Generate HTML report if requested
    if "html" in formats and MODULES_AVAILABLE:
        try:
            # Derive HTML path from markdown path if needed
            html_path = (
                output_path.replace(".md", ".html")
                if output_path.endswith(".md")
                else output_path + ".html"
            )
            html_path = generate_html_report(
                report, html_path, title=f"{procedure_name} - Interactive Report"
            )
            print(
                f"HTML report with zoomable diagrams generated successfully at {html_path}"
            )
        except Exception as e:
            print(f"Error generating HTML report: {e}")


if __name__ == "__main__":
    generate_complete_analysis_report()
