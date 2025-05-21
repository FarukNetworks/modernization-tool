from google.genai import types
import json


def get_prompt(procedure_name, procedure_definition, dependencies, project_path):
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

    # Get testable units
    with open(
        f"{project_path}/analysis/{procedure_name}/testable_units.json",
        "r",
    ) as f:
        testable_units = json.load(f)

    json_template = """
```json
{
  "id": "BF-XXX",
  "name": "Business Function Name",
  "sqlSnippet": "Relevant SQL code from the stored procedure",
  "topics": [
    {
      "question": "Common user question about this function",
      "answer": "Clear, non-technical answer based strictly on the SQL code"
    }
    // Additional question-answer pairs
  ]
}
```
"""

    prompt = f"""
# Stored Procedure Knowledge Base Creation Task

## Objective
Create a comprehensive knowledge base for the target stored procedure in a format that will help support teams explain the technical logic to non-technical users. This knowledge base will serve as a reference that clearly documents each business function and answers common user questions.

## Input Files
- **Stored Procedure Source Code**: {procedure_definition}
- **Business Functions Documentation**: {business_functions_json}
- **Business Process Documentation**: {business_processes_json}
- **Testable Units Documentation**: {testable_units}
- **Any additional supporting documentation**: 
{returnable_objects_json}
{process_object_mapping_json}
- **Dependencies**:
{dependencies}

## Process

### Phase 1: Comprehension and Analysis
1. **Understand the Stored Procedure's Purpose**:
   - Review the provided code and documentation
   - Identify the core business process(es) the procedure supports
   - Recognize the key stakeholders and end users who benefit from this procedure
   - Determine the typical usage context and business scenarios

2. **Identify Key Concepts and Components**:
   - Use the existing business functions documentation as a starting point
   - Map major functions within the procedure
   - Identify business domain terminology used
   - Note configuration parameters and their impact
   - Recognize validation rules and edge case handling
   - Understand relationships between components

3. **Anticipate Relevant Questions**:
   - Consider which aspects might be confusing to end users
   - Identify areas where calculation logic is complex
   - Note where configuration settings affect behavior
   - Consider common operational questions about timing and triggers
   - Think about troubleshooting scenarios users might encounter

### Phase 2: Knowledge Base Creation

For each identified business function, create a separate JSON file following this structure:
```json
{{
  "id": "BF-XXX",
  "name": "Business Function Name",
  "sqlSnippet": "Relevant SQL code from the stored procedure",
  "topics": [
    {{
      "question": "Common user question about this function",
      "answer": "Clear, non-technical answer based strictly on the SQL code"
    }}
    // Additional question-answer pairs
  ]
}}
```

### Content Guidelines
1. **Strict Factual Accuracy**: 
   - Only include information that is directly evident from the SQL snippet or the overall stored procedure.
   - If referencing elements outside the scope of the current business function, explicitly explain where in the stored procedure this happens.
   - Do not make assumptions or claims that cannot be verified in the provided code.

2. **Question Relevance**:
   - Address the business process cycle (setup, execution, reporting, etc.)
   - Focus on business impact and outcomes
   - Consider questions from different user perspectives and roles
   - Include comparative questions about similar concepts
   - Address common pain points and troubleshooting scenarios
   - Use terminology that business users would naturally use
   - Include "why" questions about the rationale behind implementations

3. **Answer Format**:
   - Use clear, non-technical language accessible to users with limited technical knowledge.
   - Focus on the business logic and purpose rather than implementation details.
   - Keep answers concise while being comprehensive enough to address the question.
   - When uncertain, acknowledge limitations rather than making up information.

## Output
Produce individual JSON files for each Business Function that meet the requirements above. These files will be used in a knowledge management system to provide support teams with accurate, consistent answers to user questions about the stored procedure's functionality. Save the output files to the specified location.
"""

    task = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
{prompt}

<output_format>
ONLY RESPOND JSON AND VALID JSON FOLLOWING THIS TEMPLATE:
FILE: faq.json
{json_template}
</output_format>
"""
            )
        ],
    )
    return task
