import os
import json
import re
import pyodbc
import dotenv


def get_dependencies(procedure_name, processed_objects=None):
    if processed_objects is None:
        processed_objects = set()

    # Avoid circular dependencies
    if procedure_name in processed_objects:
        return []

    processed_objects.add(procedure_name)

    # Get dependencies
    with open(os.path.join("output/data", "procedure_dependencies.json"), "r") as f:
        all_procedures = json.load(f)

    # Get object creation scripts
    with open(os.path.join("output/data", "object_create_scripts.json"), "r") as f:
        all_object_scripts = json.load(f)

    # Create a lookup dictionary for object create scripts
    create_scripts_lookup = {obj["name"]: obj for obj in all_object_scripts}

    # Find the procedure with matching name in the dependencies list
    procedure_dependencies = []
    for proc in all_procedures:
        if proc.get("name") == procedure_name:
            procedure_dependencies = proc.get("dependencies", [])
            break

    # Create connection to database to check identity columns and existing records
    dotenv.load_dotenv()
    connection_string = os.getenv("CONNECTION_STRING")
    connection = pyodbc.connect(connection_string) if connection_string else None
    cursor = connection.cursor() if connection else None

    # Create simplified dependency list with only name, type, and create script
    dependencies = []

    for dep in procedure_dependencies:
        # Split the name into schema and table parts if applicable
        name_parts = (
            dep["name"].split(".", 1) if "." in dep["name"] else [None, dep["name"]]
        )

        schema_name = name_parts[0] if len(name_parts) > 1 else None
        table_name = name_parts[1] if len(name_parts) > 1 else dep["name"]

        dependency = {
            "name": table_name,
            "schemaName": schema_name,
            "type": dep.get("type", "UNKNOWN"),
            "has_enforced_dependencies": False,  # Default value
            "auto_populated_columns": [],
        }

        # Add create script if available
        if dep["name"] in create_scripts_lookup:
            create_script = create_scripts_lookup[dep["name"]].get("definition", "")
            dependency["create_script"] = create_script

            # Check for enforced dependencies in the create script
            dependency["has_enforced_dependencies"] = check_enforced_dependencies(
                create_script
            )

            # Extract auto populated columns if it's a table
            if dep.get("type") == "TABLE" and cursor:
                auto_populated_columns = get_table_info(cursor, schema_name, table_name)
                dependency["auto_populated_columns"] = auto_populated_columns

            # If this is a view, recursively get its dependencies
            if dep.get("type") == "VIEW":
                # Get view dependencies recursively
                view_deps = get_dependencies(dep["name"], processed_objects)
                dependency["view_dependencies"] = view_deps

        dependencies.append(dependency)

    # Also add references from the create script (like temporary tables)
    main_procedure_script = create_scripts_lookup.get(procedure_name, {}).get(
        "definition"
    )
    if main_procedure_script:
        # Extract additional table references from the script
        # This regex finds potential table references in the script
        potential_refs = re.findall(
            r"(?:FROM|JOIN|INTO|UPDATE|INSERT INTO)\s+([^\s(),;]+)",
            main_procedure_script,
            re.IGNORECASE,
        )
        for ref in potential_refs:
            # Clean up the reference
            clean_ref = ref.strip("[]\"'`")

            # Skip if it's already in dependencies
            if any(dep["name"] == clean_ref.split(".")[-1] for dep in dependencies):
                continue

            # Split into schema and table parts
            ref_parts = (
                clean_ref.split(".", 1) if "." in clean_ref else [None, clean_ref]
            )
            schema_name = ref_parts[0] if len(ref_parts) > 1 else None
            table_name = ref_parts[1] if len(ref_parts) > 1 else clean_ref

            # Add to dependencies
            dependency = {
                "name": table_name,
                "schemaName": schema_name,
                "type": "REFERENCED",  # Mark as referenced but not in formal dependencies
                "has_enforced_dependencies": False,  # Default value
                "auto_populated_columns": [],
            }

            # Try to get create script
            full_name = f"{schema_name}.{table_name}" if schema_name else table_name
            if full_name in create_scripts_lookup:
                create_script = create_scripts_lookup[full_name].get("definition", "")
                dependency["create_script"] = create_script

                # Check for enforced dependencies in the create script
                dependency["has_enforced_dependencies"] = check_enforced_dependencies(
                    create_script
                )

                # Extract auto populated columns if it's not a temp table
                obj_type = create_scripts_lookup[full_name].get("type")
                dependency["type"] = obj_type  # Update type if available

                if obj_type == "TABLE" and not table_name.startswith("#") and cursor:
                    auto_populated_columns = get_table_info(
                        cursor, schema_name, table_name
                    )
                    dependency["auto_populated_columns"] = auto_populated_columns

                if obj_type == "VIEW":
                    view_deps = get_dependencies(full_name, processed_objects)
                    dependency["view_dependencies"] = view_deps

            dependencies.append(dependency)

    # Close database connection
    if connection:
        connection.close()

    return dependencies


def get_table_info(cursor, schema_name, table_name):
    """
    Get auto-populated columns for the specified table, including:
    - Identity columns
    - Computed columns
    - Columns with default values
    - Timestamp/rowversion columns
    - Columns with other auto-generation mechanisms

    Args:
        cursor: Database cursor
        schema_name: Schema name
        table_name: Table name

    Returns:
        list: List of column info dictionaries with column name and population mechanism
    """
    auto_populated_columns = []

    try:
        # Escape the names for SQL injection protection
        schema = schema_name if schema_name else "dbo"

        # Get all auto-populated columns
        cursor.execute(
            """
            SELECT 
                c.name AS column_name,
                CASE
                    WHEN c.is_identity = 1 THEN 'IDENTITY'
                    WHEN c.is_computed = 1 THEN 'COMPUTED'
                    WHEN c.default_object_id != 0 THEN 'DEFAULT'
                    WHEN t.name IN ('timestamp', 'rowversion') THEN 'ROWVERSION'
                    ELSE NULL
                END AS population_type,
                CASE
                    WHEN c.is_computed = 1 THEN cc.definition
                    WHEN c.default_object_id != 0 THEN dc.definition
                    ELSE NULL
                END AS definition
            FROM sys.columns c
            JOIN sys.tables t ON c.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            JOIN sys.types tp ON c.user_type_id = tp.user_type_id
            LEFT JOIN sys.computed_columns cc ON c.object_id = cc.object_id AND c.column_id = cc.column_id
            LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
            WHERE t.name = ? AND s.name = ?
            AND (
                c.is_identity = 1 OR
                c.is_computed = 1 OR
                c.default_object_id != 0 OR
                tp.name IN ('timestamp', 'rowversion') OR
                COLUMNPROPERTY(c.object_id, c.name, 'IsRowGuidCol') = 1
            )
        """,
            (table_name, schema),
        )

        for row in cursor.fetchall():
            col_info = {"name": row.column_name, "population_type": row.population_type}

            if row.definition:
                col_info["definition"] = row.definition

            auto_populated_columns.append(col_info)

    except Exception as e:
        print(f"{str(e)}")

    return auto_populated_columns


def check_enforced_dependencies(script):
    """
    Check if a create script contains enforced dependencies (foreign keys).

    Args:
        script (str): The SQL create script to analyze

    Returns:
        bool: True if enforced dependencies (FOREIGN KEY constraints) are found
    """
    if not script:
        return False

    # Look for FOREIGN KEY constraints
    foreign_key_patterns = [
        r"FOREIGN\s+KEY",
        r"REFERENCES\s+\w+(\.\w+)?(\s*\(\w+\))?",
        r"CONSTRAINT\s+\w+\s+FOREIGN\s+KEY",
    ]

    # Look for ALTER TABLE statements adding foreign keys
    alter_table_patterns = [
        r"ALTER\s+TABLE.*ADD\s+.*FOREIGN\s+KEY",
        r"ALTER\s+TABLE.*ADD\s+CONSTRAINT.*FOREIGN\s+KEY",
        r"ALTER\s+TABLE.*ADD\s+.*REFERENCES",
        r"WITH\s+CHECK\s+ADD\s+CONSTRAINT.*FOREIGN\s+KEY",
    ]

    # Combine all patterns
    all_patterns = foreign_key_patterns + alter_table_patterns

    for pattern in all_patterns:
        if re.search(pattern, script, re.IGNORECASE):
            return True

    return False


def analyze_procedure(procedure_name):
    dependencies = get_dependencies(procedure_name)

    for i, dep in enumerate(dependencies, 1):
        schema = dep["schemaName"] or "N/A"
        enforced = (
            "Enforced" if dep.get("has_enforced_dependencies") else "Not enforced"
        )

        auto_populated_info = "Auto-populated columns: "
        if dep.get("auto_populated_columns"):
            auto_populated_info += ", ".join(
                [col["name"] for col in dep["auto_populated_columns"]]
            )
        else:
            auto_populated_info += "None"

        # Save the dependency tree to a JSON file
        with open(
            f"output/analysis/{procedure_name}/{procedure_name}_dependency_tree.json",
            "w",
        ) as f:
            json.dump(dependencies, f, indent=2)

        print(dependencies)

        # Save the JSON
        with open(
            f"output/analysis/{procedure_name}/{procedure_name}_dependency_tree.json",
            "w",
        ) as f:
            json.dump(dependencies, f, indent=2)

    return dependencies


if __name__ == "__main__":
    procedure_name = "dbo.usp_PerformLoanUnderwritingAnalysis"
    analyze_procedure(procedure_name)
