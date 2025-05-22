"""
Report Components Module

This module contains functions for generating the various sections
of the stored procedure analysis report, such as the business purpose,
functions table, and testable units table.
"""

def extract_business_purpose(business_process, business_functions):
    """
    Extract the business purpose from the provided data.
    
    Args:
        business_process (dict): The business process data
        business_functions (dict): The business functions data
    
    Returns:
        str: Extracted business purpose text
    """
    purpose = ""
    
    # Prioritize extracting description from the businessProcesses array in the business process JSON
    if business_process and isinstance(business_process, dict) and 'businessProcesses' in business_process:
        if isinstance(business_process['businessProcesses'], list) and business_process['businessProcesses']:
            # Take description from the first process
            process = business_process['businessProcesses'][0]
            if isinstance(process, dict) and 'description' in process and process['description']:
                purpose = process['description']
                return purpose  # Return immediately if found
                
    # Fallback: try other locations if not found in the preferred location
    
    # If no purpose found, try to extract from business functions
    if not purpose and business_functions and isinstance(business_functions, dict):
        # First check if we have a nested businessFunctions array (new format)
        if 'businessFunctions' in business_functions and isinstance(business_functions['businessFunctions'], list) and business_functions['businessFunctions']:
            # Look for a function that might contain overall purpose description
            for func in business_functions['businessFunctions']:
                if isinstance(func, dict) and func.get('type') == 'process' and 'description' in func:
                    purpose += func['description']
                    break
        # If not found in the new structure, try the old structure
        elif 'description' in business_functions and business_functions['description']:
            purpose += business_functions['description']
        elif 'overview' in business_functions and business_functions['overview']:
            purpose += business_functions['overview']
    
    # Check if the business functions contain a "purposes" array
    if not purpose and business_functions and isinstance(business_functions, dict):
        if 'purposes' in business_functions and isinstance(business_functions['purposes'], list) and business_functions['purposes']:
            purpose = "Business purposes:\n\n"
            for idx, p in enumerate(business_functions['purposes'], 1):
                if isinstance(p, dict) and 'description' in p:
                    purpose += f"{idx}. {p['description']}\n"
    
    # Default message if no purpose found
    if not purpose:
        purpose = "No business purpose description available in the provided documentation."
    
    return purpose

def generate_functions_table(business_functions, testable_unit_map):
    """
    Create a table of process steps with their associated business functions and details.
    
    Args:
        business_functions (dict): The business functions data
        testable_unit_map (dict): A mapping of business function IDs to testable unit IDs
    
    Returns:
        str: Markdown table of process steps
    """
    
    table = """### Process Steps

| Step ID | Step Type | Business Function ID | Business Function Name | Business Function Description |
|---------|-----------|----------------------|------------------------|-------------------------------|
"""
    
    # Extract functions from different possible structures in business_functions
    functions = []
    if isinstance(business_functions, dict):
        if 'businessFunctions' in business_functions:
            functions = business_functions['businessFunctions']
        elif 'functions' in business_functions:
            functions = business_functions['functions']
        elif 'function_list' in business_functions:
            functions = business_functions['function_list']
    
    # Create a lookup map for business functions by ID
    function_map = {}
    for function in functions:
        if isinstance(function, dict) and 'id' in function:
            function_map[function['id']] = function
    
    # Get process steps from the business process
    steps = []
    # We'll add steps from the business process in generate_report.py
    
    # Placeholder for now - we'll need to update the calling code to pass steps
    if not steps:
        table += "| - | - | - | - | - |\n"
    
    return table

def generate_testable_units_table(testable_units):
    """
    Create a comprehensive list of testable units with their details.
    
    Args:
        testable_units (list): List of testable units data
    
    Returns:
        str: Markdown formatted list of testable units
    """
    
    result = ""
    
    if not testable_units:
        return "No testable units found."
    
    # Sort testable units by ID
    sorted_units = sorted(testable_units, key=lambda x: x.get('id', '') if isinstance(x, dict) else '')
    
    for unit in sorted_units:
        if isinstance(unit, dict):
            rule_id = unit.get('id', 'Unknown')
            name = unit.get('name', rule_id)
            category = unit.get('category', 'Uncategorized')
            description = unit.get('description', 'No description provided')
            parent_function_id = unit.get('parentFunctionId', 
                                    unit.get('businessFunctionId', 
                                    unit.get('functionId', 'Unknown')))
            
            # First try the new sqlSnippet field directly in the root object
            sql_impl = unit.get('sqlSnippet', '')
            
            # If not found, fall back to the older field locations
            if not sql_impl:
                sql_impl = unit.get('sqlImplementation', 
                                unit.get('implementation', 
                                unit.get('sql', 'No SQL implementation provided')))
                
                # Extract SQL snippet from dictionary structure
                if isinstance(sql_impl, dict):
                    # Try to extract the SQL text from the dictionary
                    if 'sqlSnippet' in sql_impl:
                        sql_impl = sql_impl.get('sqlSnippet', '')
                    elif 'sql' in sql_impl:
                        sql_impl = sql_impl.get('sql', '')
                    elif 'query' in sql_impl:
                        sql_impl = sql_impl.get('query', '')
                    elif 'text' in sql_impl:
                        sql_impl = sql_impl.get('text', '')
                    elif 'code' in sql_impl:
                        sql_impl = sql_impl.get('code', '')
                    else:
                        # Fallback to string representation if we can't find SQL
                        sql_impl = str(sql_impl)
                elif not isinstance(sql_impl, str):
                    sql_impl = str(sql_impl)  # Convert any non-string to string
            
            # Create formatted header
            result += f"### {rule_id}: {name}\n\n"
            result += f"**Category:** {category}\n\n"
            result += f"**Business Function:** {parent_function_id}\n\n"
            result += f"**Description:** {description}\n\n"
            
            # Add SQL implementation
            result += "**SQL Implementation:**\n\n```sql\n" + sql_impl + "\n```\n\n"
            
            # Add test scenarios if available
            if 'testScenarios' in unit and unit['testScenarios']:
                result += "**Test Scenarios:**\n\n"
                # Update table header with the new fields
                result += "| ID / Type | Description | Considerations |\n"
                result += "|-----------|------------|---------------|\n"
                
                for scenario in unit['testScenarios']:
                    if isinstance(scenario, dict):
                        scenario_id = scenario.get('id', 'Unknown')
                        scenario_type = scenario.get('type', 'Unknown')
                        # Use description field instead of name
                        scenario_description = scenario.get('description', 'No description provided')
                        # Add new considerations field
                        scenario_considerations = scenario.get('considerations', '')
                        
                        # Format the ID/Type cell with bold ID and smaller text for type
                        id_type_cell = f"**{scenario_id}**<br><small>{scenario_type}</small>"
                        
                        # Add row to table - now with 3 columns (ID/Type are combined)
                        result += f"| {id_type_cell} | {scenario_description} | {scenario_considerations} |\n"
                
                result += "\n"
            
            # Add a separator between units
            result += "---\n\n"
    
    return result
