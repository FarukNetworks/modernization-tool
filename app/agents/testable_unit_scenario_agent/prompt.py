from google.genai import types
import json


def get_prompt(
    procedure_name, procedure_definition, dependencies, project_path, testable_unit
):
    procedure_name_only = procedure_name.split(".")[-1]

    # business_rules
    with open(
        f"{project_path}/analysis/{procedure_name}/business_rules.json",
        "r",
    ) as f:
        business_rules_json = json.load(f)

    # business_functions
    with open(
        f"{project_path}/analysis/{procedure_name}/business_functions.json",
        "r",
    ) as f:
        business_functions_json = json.load(f)

    # business_processes
    with open(
        f"{project_path}/analysis/{procedure_name}/business_processes.json",
        "r",
    ) as f:
        business_processes_json = json.load(f)

    # returnable_objects
    with open(
        f"{project_path}/analysis/{procedure_name}/returnable_objects.json",
        "r",
    ) as f:
        returnable_objects_json = json.load(f)

    # process_object_mapping
    with open(
        f"{project_path}/analysis/{procedure_name}/process_object_mapping.json",
        "r",
    ) as f:
        process_object_mapping_json = json.load(f)

    json_template = """
```json
{
  "id": "TU-001",
  "name": "Unit Name",
  "parentFunctionId": "BF-001",
  "category": "validation|calculation|data transformation|etc",
  "description": "Concise description of functionality to test",
  "sqlSnippet": "Relevant SQL code implementing this unit",
  "entities": ["Entity1", "Entity2"],
  "testScenarios": [
    {
      "id": "TS-001",
      "type": "normal",
      "description": "Test with valid customer data should return success code and populated profile"
    },
    {
      "id": "TS-002",
      "type": "datatype",
      "description": "Test boundary values for Amount field",
      "considerations": "DECIMAL(18,2) precision boundary - need to test maximum allowed values"
    },
    {
      "id": "TS-003",
      "type": "null",
      "description": "Test with NULL values in optional fields",
      "considerations": "Procedure should handle NULL values in Address2, PhoneNumber2"
    },
    {
      "id": "TS-004",
      "type": "error",
      "description": "Test with invalid input that should trigger error handling",
      "considerations": "Procedure should return appropriate error when CustomerID doesn't exist"
    }
  ]
}
```
"""

    prompt = f"""
## Objective
You are participating in a migration project where SQL stored procedures are being converted to a different technical platform (e.g., Java/.NET microservices, Lambda functions, or ETL jobs). Your task is to enrich simplified testable units identified in a previous analysis with clear test scenarios that will guide another agent in creating TSQLT tests.

## Your Task, Enrichment
1. For each testable unit provided in the input JSON, create a detailed enrichment that describes what needs to be tested
2. Extract the relevant SQL code based on the line numbers
3. Define clear test scenarios covering essential test cases
4. Identify critical considerations for each test scenario
5. Output an individual JSON file for each testable unit

## Migration Context
The enriched testable units will be used to:
1. Guide developers in correctly implementing the migrated functionality
2. Enable a test generation agent to create comprehensive TSQLT tests
3. Ensure feature parity between the legacy stored procedure and the new implementation
4. Provide documentation for QA and business stakeholders to verify the migration's correctness

## Input
1. A JSON file containing simplified testable units with basic identification information
[{testable_unit}]
2. The original SQL stored procedure code
[{procedure_definition}]
3. Business functions JSON (for context about the broader business purposes)
[{business_functions_json}]
4. Business processes JSON (for context about process flows and orchestration)
[{business_processes_json}]
5. Returnable objects JSON (for context about data structures and return conditions)
[{returnable_objects_json}]
6. Dependencies file (containing table definitions, constraints, calculated columns, and column types)
[{dependencies}]

## Reference Materials Usage
Use the provided reference materials to:
1. Understand the business context of each testable unit based on its parent function
2. See how the testable unit contributes to the overall business process
3. Understand what data objects the testable unit affects or produces
4. Identify business rules that should be verified through test scenarios
5. Ensure test scenarios reflect realistic business cases
6. Use table definitions and constraints to identify critical test considerations

## Guidelines for Test Scenario Creation
Focus on WHAT needs to be tested, not HOW to test it. Ensure you identify test scenarios for:

1. Normal business cases with valid inputs and expected success paths
2. Edge cases (minimal required data, empty sets, minimum values)
3. Boundary conditions where business rules change behavior
4. Error conditions that should trigger specific error handling
5. Data type handling, especially for:
   - DECIMAL/NUMERIC precision and scale boundaries
   - String length limits for CHAR and VARCHAR fields
   - DATE vs DATETIME handling 
   - Integer boundaries
6. Data type conversions occurring in the code 
7. NULL handling for nullable parameters and columns
8. Each distinct business rule or calculation
9. Both successful and error paths

For each scenario, identify critical considerations that will help the test generator understand what's important to verify, but don't specify exact test values or detailed assertions - those will be determined by the test generator.

## Division of Responsibilities
- YOUR RESPONSIBILITY: Identify WHAT needs to be tested and WHY
- NEXT AGENT'S RESPONSIBILITY: Determine HOW to test with specific values and assertions

Focus on identifying comprehensive test scenarios and critical areas needing verification. The next agent will handle all implementation details including specific test data values, TSQLT structure, and assertions.

## Quality Criteria
Your enriched testable units should:
1. Be clear about what functionality needs to be tested
2. Provide sufficient test scenarios for comprehensive coverage
3. Highlight critical considerations for each scenario
4. Focus on scenario identification, not test implementation details
5. Follow the specified JSON structure exactly

Create one JSON file per testable unit to enable parallel test development and efficient handoff to the test generation agent.
"""

    task = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
{prompt}

<output_format>
ONLY RESPOND JSON AND VALID JSON FOLLOWING THIS TEMPLATE:
{json_template}
</output_format>
"""
            )
        ],
    )
    return task
