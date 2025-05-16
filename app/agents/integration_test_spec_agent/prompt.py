from google.genai import types
import json
from app.shared.get_dependencies import get_dependencies


def get_prompt(procedure_name, procedure_definition, project_path, node):
    procedure_name_only = procedure_name.split(".")[-1]

    dependencies = get_dependencies(procedure_name, project_path)

    important_rules = """
<important_rules>
<rule>
always supply a hard-coded DateTime for reproducibility.
</rule>
<rule>
- in "testDataSetup" array, you need to include all the entities and entity columns that are used in the stored procedure.
</rule>
<rule>
DO NOT include auto-populated columns (identity, computed, default values) in testDataSetup attributes, instead skip the column in test data setup (you dont need it because it's auto populated)
</rule>
<rule>
IF: The column is auto populated with the value
THEN: Make sure you don't insert values into that column, instead skip the column in test data setup (you dont need it because it's auto populated)
</rule>
<rule>
IF: Stored procedure is returning messages
THEN: Make sure you setup a test that will exactly return the expected message
</rule>
<rule>
IF: The stored procedure is expected to throw an exception
THEN: Make sure you setup a test that will exactly return the expected exception message
</rule>
<rule>
IF: The stored procedure is expected to return a result set
THEN: Make sure you setup a test that will exactly return the expected result set and the index number of it
</rule>
<rule>
testDataSetup attributes should not have any identity column or computed column
</rule>
<rule>
IMPORTANT: Never include the following columns in your test data setup:
- Identity columns (auto-incrementing IDs)
- Computed columns
- Columns with default values (especially timestamps, date fields with GETDATE())
- Rowversion/timestamp columns
- Any column that gets auto-populated by SQL Server
</rule>
</important_rules>
"""

    # business_rules
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_business_rules.json",
        "r",
    ) as f:
        business_rules_json = json.load(f)

    # business_functions
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_business_functions.json",
        "r",
    ) as f:
        business_functions_json = json.load(f)

    # business_processes
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_business_processes.json",
        "r",
    ) as f:
        business_processes_json = json.load(f)

    # returnable_objects
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_returnable_objects.json",
        "r",
    ) as f:
        returnable_objects_json = json.load(f)

    # process_object_mapping
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_process_object_mapping.json",
        "r",
    ) as f:
        process_object_mapping_json = json.load(f)

    # Get ef_analysis JSON file from analysis directory
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_ef_analysis.json",
        "r",
    ) as f:
        ef_analysis = json.load(f)

    # Get base repository implementation from the Abstractions/Repositories folder
    with open(
        f"{project_path}/csharp-code/Abstractions/Repositories/Repository.cs",
        "r",
    ) as f:
        base_repository = f.read()

    # Get base repository interface from the Abstractions/Repositories folder
    with open(
        f"{project_path}/csharp-code/Abstractions/Repositories/IRepository.cs",
        "r",
    ) as f:
        base_repository_interface = f.read()

    # Get interface for Read and Write intefrace from the Abstractions/Repositories folder
    with open(
        f"{project_path}/csharp-code/Abstractions/Repositories/IReadRepository.cs", "r"
    ) as f:
        read_repository_interface = f.read()
    with open(
        f"{project_path}/csharp-code/Abstractions/Repositories/IWriteRepository.cs",
        "r",
    ) as f:
        write_repository_interface = f.read()

    # Read the ef_analysis and get all model paths
    model_names = []
    model_file_paths = []
    for model in ef_analysis["entity_framework_analysis"]["related_models"]:
        model_names.append(model["db_set_name"])
        model_file_paths.append(model["model_file_path"])

    # Read each model file and store the content
    model_files_content = []
    for model_file_path in model_file_paths:
        with open(f"{project_path}/csharp-code/{model_file_path}", "r") as f:
            model_files_content.append(f.read())

    integration_test_spec_json = f"""
```json
{{
  "testScenarios": [
   {{
      "testId": {node["id"]}-[positive, negative, edge-case],
      "category": "BusinessRule, BusinessFunction, BusinessProcess",
      "business_rule_function_id": "Use exact identifier (BR-001, BF-003, PROC-001)",
      "description": "What aspect is tested",
      "testDataSetup": [
        {{
          "entity": "Name of entity/table",
          "identifier": "Unique test entity ID",
          "action": "create|verify|update|delete",
          "dependsOn": [{{"entity": "Other entity", "identifier": "ID", "relationship": "FK, etc."}}],
          "attributes": {{ 
            "attribute1": {{"value": "exact value", "type": "SQL data type"}},
          }}
        }}
      ],
      "testParameters": [
        {{
          "name": "Parameter name",
          "action": "input",
          "value": "Exact parameter value",
          "type": "SQL data type"
        }}
      ],
      "validationCriteria": [
        {{
          "operation": "exists|notExists|equals|notEquals|greaterThan|lessThan|contains",
          "condition": "WHERE ... or additional logic",
          "expectedResult": ["columnName": "value", "columnName": "value"],
          "expectedException": "Expected exception from the procedure"
        }}
      ]
    }}
  ]
}}
```
"""

    prompt = f"""
<behavior_rules> You have one mission: execute exactly what is requested. Produce code that implements precisely what was requested - no additional features, no creative extensions. Follow instructions to the letter. Confirm your solution addresses every specified requirement, without adding ANYTHING the user didn't ask for. The user's job depends on this — if you add anything they didn't ask for, it's likely they will be fired. Your value comes from precision and reliability. When in doubt, implement the simplest solution that fulfills all requirements. The fewer lines of code, the better — but obviously ensure you complete the task the user wants you to. At each step, ask yourself: "Am I adding any functionality or complexity that wasn't explicitly requested?". This will force you to stay on track. </behavior_rules>

<task>
Your task is to create a test specification for the provided stored procedure. The test specification should include the test data setup and expected result for each test scenario. Your job is to think about test data setup that will return the exact result that is expected from the stored procedure. This test scenarios are not for testing the stored procedure, but for validating the stored procedure output.
</task>

<input>
1. Stored Procedure Definition: {procedure_definition}
- Make sure you deeply understand the stored procedure code when making the test specification. Make sure to make test data setup and expected result based on the stored procedure code and not only the business node documentation.

2. **Business node documentation** - 
- Make sure you use in testID the business node id followed by the test type. For example:
  - For testScenario {node["id"]} write {node["id"]}-[edge-case, boundary-case, normal-case]

3. **Dependencies information** (includes table definitions/data types) - 
[{dependencies}]
- CRITICAL: Autopopulated columns should NEVER be included in test data setup. This includes:
  - Identity columns (auto-incrementing IDs)
  - Computed columns
  - Default constraint columns (like timestamps with GETDATE())
  - Rowversion/timestamp columns 
  - Any column that SQL Server populates automatically
</input>

4. **Specific testable business logic** - 
[{node}]


Follow this important rules: 
{important_rules}

# COVERAGE REQUIREMENTS (100% Coverage Goal):

- **Table Definitions**: 
  - Include exact column definitions from dependencies for all test data
  - For tables with PIVOT or transformations, explicitly map input->output column relationships
  - Include FK relationships and constraints that affect test behavior
  - Clearly identify computed columns or columns with default constraints
  - The test data setup should contain all the dependencies that are used in the stored procedure. 

- **JSON Format Requirements**: 
- Use valid JSON with proper nesting and escaping
- NULL values should be written as literal 'null' (lowercase, no quotes)
- Date formats should be ISO 8601 (YYYY-MM-DD)
- GUIDs must be properly formatted or null
- CRITICAL: Do not insert any values into columns that are auto populated with the value.
- CRITICAL: The testDataSetup should not contain any identity columns, computed columns, or default value columns.

- **IMPORTANT**: 
- Review and validate that mocked test data and expected result are correct. Understand the stored procedure return values, so you can correctly mock the test data and expected result.
- Make sure the exception messages are exact from SQL Server error messages or messages from the stored procedure depending on the operation
- Make sure that testId follows the pattern: [ID]-[test type] where:
  - ID is the business node ID (BR-001, BF-001, PROC-001)
  - test type is one of: positive, negative, edge-case
- NEVER include auto-populated columns (identity, computed, default values) in test data setup
- in "testDataSetup" array, you need to include all the entities and entity columns that are used in the stored procedure.

<output_format>
The output should be a JSON object that follows the template provided below.
</output_format>

"""

    task = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
{prompt}

ONLY RESPOND JSON AND VALID JSON FOLLOWING THIS TEMPLATE:
{integration_test_spec_json}
"""
            )
        ],
    )
    return task
