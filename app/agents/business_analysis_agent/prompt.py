from google.genai import types
import json
import os
import glob

business_rules_json = """
```json
   {
     "businessRules": [
       {
         "id": "BR-001",
         "name": "Rule Name",
         "action": "Brief description of action",
         "category": "configuration|validation|calculation|data transformation|audit|security|etc",
         "description": "Detailed description of the business rule",
         "trigger": "When/how this rule is triggered",
         "entities": ["Entity1", "Entity2"],
         "implementation": {
           "sqlSnippet": "Relevant SQL code implementing this rule",
           "technicalDescription": "Technical description of implementation",
           "lineStart": 10,
           "lineEnd": 11,
           "technicalNotes": "Any additional implementation notes important for the developer"
         },
         "confidenceScore": 95,
         "reasoning": "Reasoning behind identification of this business rule",
         "testValues": {
           "normalCases": ["Example1", "Example2"],
           "boundaryCases": ["BoundaryExample1"],
           "edgeCases": ["EdgeExample1"]
         },
         "technicalImplications": {
           "dataStructure": "Notes about data structure implications",
           "performance": "Notes about performance considerations"
         },
         "testableIntent": true
       }
     ]
   }
   ```
"""

business_functions_json = """
```json
{
  "businessFunctions": [
    {
      "id": "BF-001",
      "name": "Function Name",
      "type": "process",
      "sqlSnippet": "Relevant SQL code implementing this rule",
      "description": "Detailed description of the function",
      "businessPurpose": "Explanation of why this function exists from a business perspective",
      "businessContext": "Broader business context and terminology",
      "testableUnits": ["TU-001", "TU-002"],
      "dataRequirements": {
        "inputs": ["Input1", "Input2"],
        "outputs": ["Output1", "Output2"],
        "dependencies": ["Dependency1"]
      },
      "technicalContext": {
        "dataTransformation": "Notes about data transformation",
        "dynamicStructure": "Notes about dynamic structures",
        "dataFlow": "Notes about data flow",
      },
      "reusability": {
        "usedInProcesses": ["PROC-001"],
        "usedInSteps": ["STEP-001", "STEP-003"]
      }
    },
    {
      "id": "BF-002",
      "name": "Parameter Name",
      "type": "configuration",
      "description": "Detailed description of the configuration parameter",
      "businessPurpose": "Explanation of why this parameter exists and its business meaning",
      "businessContext": "Broader business context for this configuration",
      "parameterDetails": {
        "name": "@ParameterName",
        "value": "90",
        "unit": "days",
        "shouldExternalize": true,
        "changeImpact": "Description of how changing this value affects business outcomes"
      },
      "testableUnits": ["TU-003"],
      "dataRequirements": {
        "inputs": [],
        "outputs": ["Output1"],
        "dependencies": []
      },
      "technicalContext": {
        "dataTransformation": "How this parameter affects transformations",
        "dynamicStructure": "Whether it affects dynamic behavior",
        "dataFlow": "How this parameter flows through the code"
      },
      "reusability": {
        "usedInProcesses": ["PROC-001"],
        "usedInSteps": ["STEP-002"]
      }
    }
  ]
}
```
"""

business_processes_json = """
```json
{
  "businessProcesses": [
    {
      "id": "PROC-001",
      "name": "Process Name",
      "description": "Description of what the stored procedure does",
      "orchestration": {
        "steps": [
          {
            "id": "STEP-001",
            "sequence": 1,
            "name": "Step Name",
            "type": "process|decision|data-retrieval|validation|calculation|terminal",
            "description": "Description of this step",
            "businessFunctionRef": "BF-001",
            "implementation": "Notes about technical implementation",
            "inputs": ["Input1"],
            "outputs": ["Output1"],
            "controlFlow": {
              "type": "standard|decision|terminal|merge",
              // For standard type:
              "nextStep": "STEP-002",
              
              // For decision type:
              "conditions": [
                {
                  "condition": "Condition description",
                  "outcome": "success|error|continue",
                  "nextStep": "STEP-003",
                  "terminatesExecution": false
                },
                {
                  "condition": "Alternative condition description",
                  "outcome": "error",
                  "nextStep": null,
                  "terminatesExecution": true,
                  "returnsDescription": "Description of error or result returned"
                }
              ],
              
              // For terminal type:
              "terminatesExecution": true,
              "returnsDescription": "Description of final result",
              
              // For merge type:
              "mergeFrom": ["STEP-003", "STEP-004"],
              "nextStep": "STEP-005"
            }
          }
        ]
      }
    }
  ]
}
```
"""

returnable_objects_json = """
```json
{
  "returnableObjects": [
    {
      "id": "RO-001",
      "name": "Object Name",
      "description": "Description of the returnable object",
      "structure": {
        "type": "resultSet|integerCode|etc",
        "columns": [
          {"name": "Column1", "type": "DataType", "description": "Description"}
        ]
      },
      "relatedBusinessProcess": "PROC-001",
      "returnConditions": [
        {
          "processStepId": "STEP-002",
          "businessFunctionId": "BF-003",
          "condition": "Condition under which this is returned",
          "description": "Description of when/why returned"
        }
      ],
      "technicalNotes": "Technical notes about this returnable",
    }
  ],
  "returnScenarios": [
    {
      "id": "RS-001",
      "name": "Scenario Name",
      "description": "Description of this return scenario",
      "returnedObjects": [
        {
          "objectId": "RO-001",
          "description": "Description in this scenario",
          "isRequired": true
        }
      ],
      "triggerCondition": "Condition that triggers this scenario"
    }
  ],
  "sideEffects": {
    "description": "Side effects produced by the stored procedure",
    "effects": [
      {
        "id": "SE-001",
        "name": "Side Effect Name",
        "description": "Description of side effect",
        "affectedEntities": ["Entity1"],
        "producedInScenarios": ["RS-001"],
        "producedByFunctions": ["BF-002"],
        "dataWritten": {
          "Field1": "Description of data written",
          "Field2": "Description of data written"
        },
      }
    ]
  }
}
```
"""

process_object_mapping_json = """
```json
{
  "processObjectMapping": {
    "description": "Maps business processes and steps to returnable objects and conditions",
    "mappings": [
      {
        "processId": "PROC-001",
        "processName": "Process Name",
        "flowPaths": [
          {
            "pathId": "PATH-001",
            "description": "Description of this path",
            "steps": ["STEP-001", "STEP-002"],
            "conditionalTrigger": "Condition triggering this path",
            "returnableObjects": [
              {
                "objectId": "RO-001",
                "generatedInStep": "STEP-002",
                "generatedByFunction": "BF-003",
                "description": "Description of object in this context",
                "notes": "Additional notes"
              }
            ]
          }
        ]
      }
    ],
    "decisionPoints": [
      {
        "decisionId": "DP-001",
        "description": "Description of decision point",
        "decisionVariable": "Variable name",
        "implementedByFunction": "BF-004",
        "outcomes": [
          {
            "value": "Value for this outcome",
            "resultingPath": "PATH-001",
            "returnObjectIds": ["RO-001"]
          }
        ]
      }
    ],
    "executionOutcomes": {
      "description": "Detailed outcomes of the stored procedure execution",
      "outcomes": [
        {
          "outcomeId": "OC-001",
          "description": "Description of this outcome",
          "conditions": ["Condition1", "Condition2"],
          "returnsData": true,
          "returnableObjects": ["RO-001", "RO-002"],
          "databaseEffects": [
            {
              "effect": "Description of database effect",
              "details": "Additional details",
              "relatedSideEffect": "SE-001",
              "implementedByFunction": "BF-005"
            }
          ],
          "flowPath": "PATH-001"
        }
      ]
    }
  }
}
```
"""

testable_units_json = """
```json
{
  "testableUnits": [
    {
      "id": "TU-001",
      "name": "Unit Name",
      "parentFunctionId": "BF-001",
      "category": "validation|calculation|data transformation|etc",
      "coverage": {
        "codeLines": [10, 11]
      }
    }
  ]
}
```
"""


def get_prompt(procedure_name, procedure_definition, dependencies):

    prompt = f"""
## Objective
Analyze the provided SQL stored procedure using both the SQL code and static analysis data to decompose it into two main structures:
1. Execution Flow: Steps, processes, and control flow
2. Business Logic: Functions and testable units


## Your Task
1. For all other components (business functions, processes, objects, mappings): Create fully populated detailed structures
2. Ensure every aspect of the SQL code is covered by at least one testable unit
3. Use your own analysis and judgment to identify the structure, using static analysis data as a reference but not as the sole determinant

## Conceptual Framework
Consider the SQL procedure as containing two interrelated tracks:

1. Execution Flow Track:
   - Business processes represent end-to-end workflows
   - Steps define the sequence of actions within a process
   - Each step references a business function that implements its logic

2. Business Logic Track:
   - Business functions represent logical capabilities that can be reused
   - Functions contain the actual implementation details

## Provided Files
1. The original SQL stored procedure code
[{procedure_definition}]
2. The stored procedure dependencies
[{dependencies}]


## Control Flow Types:
- "decision": Use for IF/ELSE blocks, CASE statements, or loop constructs
- "standard": Use for sequential statements without branching or looping
- "terminal": Use for final steps that return data or end execution
- "merge": Use when multiple flow paths converge

Ensure that every aspect of the SQL code is covered by at least one testable unit, with no gaps in coverage.
Take the time to review the outputs and make sure they truly reflect the content of the stored procedure.
```
"""

    task = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
{prompt}

ALWAYS RESPOND WITH: 
FILE: <file_name>
```json
<code>
```

Response should have 3 files: 

FILE: business_rules.json
FILE: business_functions.json
FILE: business_processes.json

The respond should look like this:

FILE: business_rules.json
{business_rules_json}

FILE: business_functions.json
{business_functions_json}

FILE: business_processes.json
{business_processes_json}
"""
            )
        ],
    )
    return task


def get_returnable_objects_prompt(
    procedure_name, project_path, procedure_definition, dependencies
):
    """Generate the prompt for returnable objects analysis with robust error handling"""
    try:
        import glob

        # Define the analysis directory
        analysis_dir = os.path.join(project_path, "analysis", procedure_name)

        if not os.path.exists(analysis_dir):
            print(f"Error: Analysis directory not found at {analysis_dir}")
            return None

        # Use glob pattern matching to find the files regardless of exact name
        business_rules_files = glob.glob(
            os.path.join(analysis_dir, "business_rules.json")
        )
        business_functions_files = glob.glob(
            os.path.join(analysis_dir, "business_functions.json")
        )
        business_processes_files = glob.glob(
            os.path.join(analysis_dir, "business_processes.json")
        )

        if not business_rules_files:
            print(f"Error: No business rules file found in {analysis_dir}")
            return None

        if not business_functions_files:
            print(f"Error: No business functions file found in {analysis_dir}")
            return None

        if not business_processes_files:
            print(f"Error: No business processes file found in {analysis_dir}")
            return None

        # Use the first matching file for each type
        business_rules_path = business_rules_files[0]
        business_functions_path = business_functions_files[0]
        business_processes_path = business_processes_files[0]

        print(f"Found business rules file: {os.path.basename(business_rules_path)}")
        print(
            f"Found business functions file: {os.path.basename(business_functions_path)}"
        )
        print(
            f"Found business processes file: {os.path.basename(business_processes_path)}"
        )

        # Read the files
        with open(business_rules_path, "r") as f:
            business_rules = json.load(f)

        with open(business_functions_path, "r") as f:
            business_functions = json.load(f)

        with open(business_processes_path, "r") as f:
            business_processes = json.load(f)

        prompt = f"""
## Objective
Analyze the provided SQL stored procedure using both the SQL code and static analysis data to decompose it into two main structures:
1. Execution Flow: Steps, processes, and control flow
2. Business Logic: Functions and testable units


## Your Task
1. Thoroughly analyze the SQL stored procedure and reference the static analysis data as a helpful guide
2. For testable units: Create simplified skeletal structures focusing on identification and categorization
3. For all other components (business functions, processes, objects, mappings): Create fully populated detailed structures
4. Ensure every aspect of the SQL code is covered by at least one testable unit
5. Use your own analysis and judgment to identify the structure, using static analysis data as a reference but not as the sole determinant

## Conceptual Framework
Consider the SQL procedure as containing two interrelated tracks:

1. Execution Flow Track:
   - Business processes represent end-to-end workflows
   - Steps define the sequence of actions within a process
   - Each step references a business function that implements its logic

2. Business Logic Track:
   - Business functions represent logical capabilities that can be reused
   - Testable units are atomic, verifiable units of business logic within functions
   - Functions contain the actual implementation details

Object mappings create connections between both tracks by linking steps, functions, and data objects.

## Static Analysis as Reference Only
The static analysis data (analysis.json) is provided as a helpful reference, but you should make your own determinations about:
- What constitutes a testable unit
- How business functions should be organized
- What processes are present in the code
- What objects are returned and under what conditions

Use the static analysis to inform your work, but critically evaluate its suggestions and make independent judgments about the code's structure and meaning.

## Focus for Testable Units
For testable units, focus on:
1. IDENTIFICATION: Unique ID and descriptive name
2. CATEGORIZATION: Functional category
3. PARENT RELATIONSHIP: Link to parent business function
4. CODE BOUNDARIES: Line numbers where the unit begins and ends


## Provided Files
1. The original SQL stored procedure code
[{procedure_definition}]
2. The stored procedure dependencies
[{dependencies}]


## Control Flow Types:
- "decision": Use for IF/ELSE blocks, CASE statements, or loop constructs
- "standard": Use for sequential statements without branching or looping
- "terminal": Use for final steps that return data or end execution
- "merge": Use when multiple flow paths converge

Ensure that every aspect of the SQL code is covered by at least one testable unit, with no gaps in coverage.
Take the time to review the outputs and make sure they truly reflect the content of the stored procedure.

## Business Analysis Files:
1. {business_rules}
2. {business_functions}
3. {business_processes}

## Deliverables
Produce exactly 2 JSON files:
1. returnable_objects.json  
2. process_object_mapping.json
3. testable_units.json

ALWAYS RESPOND WITH: 
FILE: <file_name>
```json
<code>
```

The response should have 2 files with the following structure: 

FILE: returnable_objects.json
{returnable_objects_json}

FILE: process_object_mapping.json
{process_object_mapping_json}

FILE: testable_units.json
{testable_units_json}
"""

        return prompt

    except Exception as e:
        print(f"Error preparing returnable objects prompt: {str(e)}")
        import traceback

        traceback.print_exc()
        return None
