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
         "description": "Detailed description of the function",
         "rules": ["BR-001", "BR-002"],
         "dataRequirements": {
           "inputs": ["Input1", "Input2"],
           "outputs": ["Output1", "Output2"],
           "dependencies": ["Dependency1"]
         },
         "technicalContext": {
           "dataTransformation": "Notes about data transformation",
           "dynamicStructure": "Notes about dynamic structures",
           "performanceConsiderations": "Notes about performance",
           "dataFlow": "Notes about data flow" 
         },
         "testableIntent": true
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
         "description": "Detailed description of the process",
         "orchestration": {
           "steps": [
             {
               "id": "STEP-001",
               "sequence": 1,
               "functionId": "BF-001",
               "type": "type of step",
               "description": "Description of this step",
               "inputs": ["Input1"],
               "outputs": ["Output1"],
               "businessRules": ["BR-001"],
               "technicalContext": {
                 "implementation": "Notes about technical implementation",
                 "dependencies": "Notes about technical dependencies",
                 "dataFlow": "Notes about data flow"
               },
               "testableIntent": true,
               "controlFlow": {
                 "type": "standard|conditional|loop",
                 "nextStep": "STEP-002"
               }
             }
           ],
           "technicalDependencies": [
             {
               "description": "Description of dependency",
               "detail": "Detailed explanation",
               "impact": "Impact on implementation",
               "testableIntent": false
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
          "condition": "Condition under which this is returned",
          "description": "Description of when/why returned"
        }
      ],
      "technicalNotes": "Technical notes about this returnable",
      "testableIntent": true
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
      "businessRulesInvolved": ["BR-001"],
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
        "dataWritten": {
          "Field1": "Description of data written",
          "Field2": "Description of data written"
        },
        "businessRules": ["BR-001"]
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
              "relatedSideEffect": "SE-001"
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


def get_prompt(procedure_name, procedure_definition, dependencies):

    prompt = f"""
<behavior_rules>
You have one mission: execute exactly what is requested. 
Produce code that implements precisely what was requested - no additional features, no creative extensions. 
Follow instructions to the letter. Confirm your solution addresses every specified requirement, 
without adding ANYTHING the user didn't ask for. 
Do not assume anything about the analysis of the code and instead think through the code step by step.
</behavior_rules>

## Objective
Analyze the provided SQL stored procedure and decompose it into structured business components, rules, processes, and technical patterns to prepare for a modern implementation. The output should be detailed JSON files that document both the business logic and critical technical implementation patterns.

## Your Task
1. Thoroughly analyze the SQL stored procedure and any supporting files
2. Extract and document all business rules and technical patterns
3. Identify key business functions and their implementation requirements
4. Map the overall process flow, including branching and looping logic
5. Distinguish between testable business intent and implementation-specific details
6. Document all returnable objects and the conditions under which they are returned

## Provided Files
1. The original SQL stored procedure [{procedure_definition}]
2. The dependencies of the procedure [{dependencies}]

### Important Detailing Requirements
- If the stored procedure uses or implies a PIVOT or other data transformations, list any **pivot columns** (or analogous transformations) in the final JSON where applicable (business rules or processes).
- If the procedure handles errors (e.g., using `@@ERROR`, RAISERROR, try/catch), identify **how errors are captured** and **how log messages** (or error messages) are constructed.
- Note **parameter usage**: which parameters the procedure expects, how they affect the logic or the final output, and how they might appear in log messages (e.g., start date, load identifier, etc.).
- Highlight any **branching** or **conditional checks** (IF/ELSE) and how they relate to the business process (e.g., if a package is disabled, if a certain column is zero, etc.).
- Provide a short explanation or reasoning for each extracted rule or function, plus any confidence scores where you feel uncertain.


## Analysis Guidelines
1. Focus primarily on the business intent rather than technical implementation
2. Identify implicit business rules that may not be explicitly documented
3. Note any areas where business logic seems unclear and would benefit from further clarification
4. Document any apparent data quality assumptions or edge case handling
5. Include confidence scores for your analysis when uncertainty exists
6. Use clear, consistent naming conventions throughout your analysis
7. Distinguish between testable business rules and implementation-specific technical patterns
8. Document critical technical patterns that are essential to understanding the procedure's operation
9. Identify where dynamic SQL generation or pivoting operations occur and explain their business purpose

## Technical Context Documentation
When documenting technical context, ensure you capture:

1. **Data Transformation Patterns**: How data is manipulated, especially for pivoting row data to columns
2. **Dynamic Structure Creation**: How variable-sized data sets are handled
3. **Conditional Processing**: How the procedure branches based on data conditions
4. **Data Flow**: How data moves between different processing steps
5. **Performance Considerations**: Areas where performance optimization is important
6. **Test Intent**: Whether each element represents testable business behavior or implementation detail

## Returnable Objects Documentation
When documenting returnable objects, ensure you capture:

1. **Result Sets**: All data sets returned by the procedure and their structures
2. **Return Conditions**: The exact conditions under which each object is returned
3. **Implicit Returns**: Any implicit return values generated by the procedure
4. **Side Effects**: Database modifications or other side effects that occur during execution
5. **Process Mapping**: Clear mapping between execution paths and returnable objects
6. **Execution Outcomes**: Complete analysis of all possible execution outcomes and what is returned in each case

## Distinguishing Testable Intent
Mark each business rule, function, and process step with a "testableIntent" flag:
- Set to "true" for elements that represent business behavior that should be explicitly tested
- Set to "false" for elements that are primarily implementation details

For example, a business rule about data validation is testable business intent, while a rule about temporary table creation is an implementation detail.

You must capture all business rules, functions, and processes that are relevant to the procedure. 
"""

    task = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
{prompt}

## Deliverables
Produce exactly 3 JSON files:
1. business_rules.json
2. business_functions.json
3. business_processes.json

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


def get_returnable_objects_prompt(procedure_name, project_path):
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
Analyze the provided business analysis files and generate returnable objects and process-object mapping files.

## Business Analysis Files:
1. {business_rules}
2. {business_functions}
3. {business_processes}

## Deliverables
Produce exactly 2 JSON files:
1. returnable_objects.json  
2. process_object_mapping.json

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
"""

        return prompt

    except Exception as e:
        print(f"Error preparing returnable objects prompt: {str(e)}")
        import traceback

        traceback.print_exc()
        return None
