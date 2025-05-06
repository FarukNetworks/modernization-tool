import pyodbc
import questionary
from questionary import Choice
import sqlparse
import os


def extract_stored_procedures(project_path, connection_string):
    """Extract stored procedures from the database."""
    try:
        # Connect to the database
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Query to get all stored procedures
        cursor.execute(
            """
            SELECT
                s.name + '.' + p.name AS name
            FROM sys.procedures p
            JOIN sys.schemas s ON p.schema_id = s.schema_id
            WHERE p.type = 'P'
            AND (s.name != 'tSQLt' AND p.name NOT LIKE 'tSQLt%')
            ORDER BY s.name, p.name;
            """
        )

        procedures = cursor.fetchall()

        if not procedures:
            print("No stored procedures found in the database.")
            connection.close()
            return

        stored_procedures = [procedure.name for procedure in procedures]

        # Create choices with SELECT ALL option at the top
        procedure_choices = [Choice(title="SELECT ALL", value="SELECT_ALL")] + [
            Choice(title=proc, value=proc) for proc in stored_procedures
        ]

        # Use checkbox selection
        selected = questionary.checkbox(
            "Select stored procedures (SPACE to select, ENTER to confirm):",
            choices=procedure_choices,
        ).ask()

        if not selected:
            print("No procedures selected. Exiting extraction process.")
            connection.close()
            return

        # If SELECT ALL is chosen, return all procedures
        if "SELECT_ALL" in selected:
            selected_procedures = stored_procedures
        else:
            selected_procedures = selected

        print(f"Selected {len(selected_procedures)} procedures for extraction.")

        # Create directories for storing extracted procedures
        sql_raw_dir = os.path.join(project_path, "sql_raw")
        analysis_dir = os.path.join(project_path, "analysis")

        if not os.path.exists(sql_raw_dir):
            os.makedirs(sql_raw_dir)

        if not os.path.exists(analysis_dir):
            os.makedirs(analysis_dir)

        # Extract each selected procedure
        for procedure_name in selected_procedures:
            print(f"Extracting: {procedure_name}")

            # Get the procedure definition
            cursor.execute(
                f"""SELECT definition FROM sys.sql_modules WHERE object_id = OBJECT_ID('{procedure_name}')"""
            )

            definition_row = cursor.fetchone()
            if not definition_row:
                print(f"Could not retrieve definition for {procedure_name}. Skipping.")
                continue

            procedure_definition = definition_row.definition

            # Remove SQL comments using sqlparse
            procedure_definition = sqlparse.format(
                procedure_definition, strip_comments=True
            ).strip()

            # Save Definition to sql-raw folder
            proc_sql_dir = os.path.join(sql_raw_dir, procedure_name)
            os.makedirs(proc_sql_dir, exist_ok=True)

            # Save the result to a SQL file
            with open(os.path.join(proc_sql_dir, f"{procedure_name}.sql"), "w") as f:
                f.write(procedure_definition)

            # Create analysis directory for the selected procedure
            proc_analysis_dir = os.path.join(analysis_dir, procedure_name)
            os.makedirs(proc_analysis_dir, exist_ok=True)

            print(f"✅ Extracted {procedure_name}")

        # Close the database connection
        connection.close()
        print(
            f"Extraction completed for all {len(selected_procedures)} selected procedures."
        )

    except Exception as e:
        print(f"Error during stored procedure extraction: {str(e)}")
        return
