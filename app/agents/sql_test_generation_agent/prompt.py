from google.genai import types
import json
from app.shared.get_dependencies import get_dependencies
import os


def get_prompt(procedure_name, procedure_definition, project_path, scenario):
    """
    Generate prompt for SQL test generation

    Args:
        procedure_name: Name of the procedure
        procedure_definition: SQL code of the procedure
        project_path: Project path
        scenario: Integration test scenario

    Returns:
        Prompt for the agent
    """
    procedure_name_only = procedure_name.split(".")[-1]
    procedure_schema = procedure_name.split(".")[0]

    # Get dependencies
    dependencies = get_dependencies(procedure_name, project_path)

    # Extract scenario details
    scenario_id = scenario.get("testId", "unknown")
    description = scenario.get("description", "")
    test_inputs = scenario.get("inputs", [])
    validation_criteria = scenario.get("validationCriteria", {})

    # Generate steps guidance for the test
    steps = """
    -- STEP 1: Declare test variables
    
    -- STEP 2: Setup test environment - All tables should be faked: tSQLt.FakeTable schema.TableNameWithoutSchema
    -- STEP 3: Setup test environment - All constraints should be applied: tSQLt.ApplyConstraint schema.TableNameWithoutSchema, constraint
    -- STEP 4: Setup test environment - All procedures should be spied: tSQLt.SpyProcedure schema.procedureName (if procedure is calling a stored procedure)
    
    -- STEP 5: Insert only the required test data as specified in the integration test spec, but DO NOT USE IDENTITY, OR ANY OTHER AUTO INCREMENTED COLUMNS
    
    -- STEP 6: Create a #resultSet temp table with the same columns as the result set from the stored procedure
    
    -- STEP 7: Use tSQLt.ResultSetFilter to execute the stored procedure and capture the results:  
    INSERT INTO #resultSet
    EXEC tSQLt.ResultSetFilter @indexOfResultSet (starting from 1, cannot be 0), '@procedure_name @parameter_name')
    If there are expected exceptions, make sure to execute the stored procedure (EXEC @procedure_name @parameter_name) without tSQLt.ResultSetFilter
    And then execute tSQLt.ExpectException with the expected exception

    -- STEP 8: Get the validationCriteria expectedResult from the integration test spec and create the #expected and #actual temp tables with specified columns.
    -- STEP 9: Insert the expectedResult into #expected
    -- STEP 10: Capture the actual result INSERT INTO #actual (column1, column2) SELECT column1, column2 FROM #resultSet; using the same columns as in #expected
    
    -- STEP 11: Only validate the result columns that are specified in the validationCriteria using temp tables #expected and #actual.

    -- STEP 12: Drop all the temp tables created in the test 
    """

    # Try to load returnable objects from multiple possible locations
    returnable_objects = []

    # Define directory paths
    output_dir_app = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "output",
    )
    output_dir_project = os.path.join(project_path, "output")

    # Generate possible filenames
    filenames = [f"returnable_objects.json"]

    # Initialize possible paths with basic locations
    possible_returnable_paths = []
    for filename in filenames:
        # Direct in analysis directory
        possible_returnable_paths.append(
            os.path.join(project_path, "analysis", procedure_name, filename)
        )
        # Direct in output directory
        possible_returnable_paths.append(
            os.path.join(project_path, "output", procedure_name, filename)
        )

    # Add project-specific output paths
    if os.path.exists(output_dir_project):
        for dir_name in os.listdir(output_dir_project):
            if os.path.isdir(os.path.join(output_dir_project, dir_name)):
                for filename in filenames:
                    possible_returnable_paths.append(
                        os.path.join(
                            output_dir_project,
                            dir_name,
                            "analysis",
                            procedure_name,
                            filename,
                        )
                    )

    # Add app-level output paths
    if os.path.exists(output_dir_app):
        for dir_name in os.listdir(output_dir_app):
            if os.path.isdir(os.path.join(output_dir_app, dir_name)):
                for filename in filenames:
                    possible_returnable_paths.append(
                        os.path.join(
                            output_dir_app,
                            dir_name,
                            "analysis",
                            procedure_name,
                            filename,
                        )
                    )

    for path in possible_returnable_paths:
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    returnable_objects = json.load(f)
                break  # Found and loaded the file, exit the loop
        except Exception as e:
            print(f"Warning: Could not load returnable objects from {path}: {str(e)}")

    if not returnable_objects:
        print(f"Warning: Could not find returnable objects for {procedure_name}")
        print(f"Tried the following paths:")
        for path in possible_returnable_paths:
            print(f"  - {path}")

    # Format the prompt
    prompt = f"""
I need you to generate a tSQLt test for the provided stored procedure following the integration test specification. The test class is already defined in the file so you don't need to include the EXEC tSQLt.NewTestClass statement.

---
### 🔧 **Input Specification**
- **Procedure name**: `{procedure_name_only}`
- **Procedure schema**: `{procedure_schema}`
- **Integration Test Specification Scenario**:
  {json.dumps(scenario, indent=2)}
  
- **Returnable objects**: {json.dumps(returnable_objects, indent=2)}
- **Stored Procedure Code**:
  ```sql
  {procedure_definition}
  ```
- **Dependencies and Schema Definitions**:
  ```sql
  {dependencies}
  ```

Follow this structure and step for test scenario: 
CREATE PROCEDURE [test_{procedure_name}].[test_{procedure_name}_{scenario_id}]
AS
BEGIN

    {steps}

END;
GO

Important rules:
1. Create test with name: [test_{procedure_name}].[test_{procedure_name}_{scenario_id}]
2. Generate complete, runnable SQL test code that follows tSQLt test patterns
3. Include proper table faking and test data setup based on the scenario
4. Validate only the specific columns mentioned in the validation criteria
5. Follow the steps outlined above
6. DO NOT include EXEC tSQLt.NewTestClass statements - this will be added automatically at the file level

Return only valid SQL code without explanations or markdown. Start directly with CREATE PROCEDURE.
"""

    return prompt
