import json


def bf_functions_template(data):
    # Format topics as markdown
    topics_markdown = ""
    for topic in data["topics"]:
        topics_markdown += f"#### Q: {topic['question']}\n\nA: {topic['answer']}\n\n"

    # Create SQL snippet section based on business function type
    sql_section = ""
    if "sqlSnippet" in data:
        sql_section = f"""### SQL Snippet
```sql
{data["sqlSnippet"]}
```
"""
    elif "type" in data and data["type"] == "configuration":
        sql_section = f"""### Configuration Details
- Parameter: {data.get("parameterName", "N/A")}
- Value: {data.get("parameterValue", "N/A")}
"""

    return f"""
## {data["name"]}

### Description
{data["description"]}

### Business Purpose
{data["businessPurpose"]}

{sql_section}
### Topics
{topics_markdown}
"""


def run_generate_bf_markdown(procedure, project_path):
    markdown_path = f"{project_path}/analysis/{procedure}/business_functions.md"

    faq_path = f"{project_path}/analysis/{procedure}/faq.json"
    with open(faq_path, "r") as f:
        faq_data = json.load(f)

    bf_functions_path = f"{project_path}/analysis/{procedure}/business_functions.json"
    with open(bf_functions_path, "r") as f:
        bf_functions_data = json.load(f)

    business_functions = bf_functions_data["businessFunctions"]
    faqs = faq_data["faqs"]

    final_markdown = "# Business Functions\n\n"

    for bf in business_functions:
        bf_id = bf["id"]
        # Find matching FAQ
        matching_faqs = [faq for faq in faqs if faq["id"] == bf_id]

        if matching_faqs:
            matching_faq = matching_faqs[0]

            # Create data structure for template
            template_data = {
                "name": f"{bf['id']}: {bf['name']}",
                "description": bf["description"],
                "businessPurpose": bf["businessPurpose"],
                "type": bf.get("type", "process"),
                "topics": matching_faq["topics"],
            }

            # Add sqlSnippet if it exists
            if "sqlSnippet" in bf:
                template_data["sqlSnippet"] = bf["sqlSnippet"]
            # Add parameter details if it's a configuration type
            elif bf.get("type") == "configuration" and "parameterDetails" in bf:
                template_data["parameterName"] = bf["parameterDetails"].get("name", "")
                template_data["parameterValue"] = bf["parameterDetails"].get(
                    "value", ""
                )

            final_markdown += bf_functions_template(template_data)

    with open(markdown_path, "w") as f:
        f.write(final_markdown)
