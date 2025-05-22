"""
Data Loader Module

This module is responsible for loading and processing the stored procedure files,
including SQL code, business functions, business processes, and testable units.
It now reads configuration from a text file with absolute paths.
"""

import os
import json

def parse_config_file(config_path):
    """
    Parse the configuration file containing absolute paths to required files.
    
    Args:
        config_path (str): Path to the configuration file
    
    Returns:
        dict: Dictionary with paths to SQL file, business functions file, 
              business processes file, and testable units folder
    """
    config = {
        'sql_file_path': None,
        'business_functions_path': None,
        'business_process_path': None,
        'testable_units_folder': None,
        'output_file_path': None,
        'output_formats': ['md']  # Default to markdown only
    }
    
    try:
        with open(config_path, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            # Skip comments and empty lines
            if line.startswith('#') or not line:
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip().lower()
                value = value.strip()
                
                # Map the config keys to our internal keys
                if key == 'sql_file' or key == 'sql_file_path':
                    config['sql_file_path'] = value
                elif key == 'business_functions' or key == 'business_functions_path':
                    config['business_functions_path'] = value
                elif key == 'business_process' or key == 'business_process_path':
                    config['business_process_path'] = value
                elif key == 'testable_units' or key == 'testable_units_folder':
                    config['testable_units_folder'] = value
                elif key == 'output_file' or key == 'output_file_path':
                    config['output_file_path'] = value
                elif key == 'output_format' or key == 'output_formats':
                    # Parse comma-separated list of formats
                    formats = [fmt.strip().lower() for fmt in value.split(',')]
                    config['output_formats'] = formats
        
        # Validate required paths
        missing_paths = [k for k, v in config.items() if v is None and k != 'output_file_path']
        if missing_paths:
            print(f"Warning: Missing required paths in config file: {', '.join(missing_paths)}")
        
        return config
        
    except Exception as e:
        print(f"Error reading configuration file: {e}")
        return config

def load_sql_code(procedure_path):
    """
    Load the SQL code from the stored procedure file.
    
    Args:
        procedure_path (str): Path to the SQL file
    
    Returns:
        str: SQL code as a string
    """
    try:
        with open(procedure_path, 'r') as f:
            sql_code = f.read()
        print(f"Successfully read SQL code from {procedure_path}")
        return sql_code
    except Exception as e:
        print(f"Error reading SQL file: {e}")
        return "SQL code file not found or could not be read"

def load_json_file(file_path, default_value, file_type=""):
    """
    Load and parse a JSON file.
    
    Args:
        file_path (str): Path to the JSON file
        default_value: Default value to return if file cannot be read
        file_type (str, optional): Type of file for logging purposes
    
    Returns:
        dict: Parsed JSON data or default value if file cannot be read
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print(f"Successfully read {file_type} from {file_path}")
        return data
    except Exception as e:
        print(f"Error reading {file_type} file: {e}")
        return default_value

def load_testable_units(folder_path):
    """
    Load all testable unit files from a folder and map them to business functions.
    
    Args:
        folder_path (str): Path to the folder containing testable unit JSON files
    
    Returns:
        tuple: (testable_units, testable_unit_map)
            - testable_units: List of all testable units
            - testable_unit_map: Dictionary mapping business function IDs to testable unit IDs
    """
    testable_units = []
    testable_unit_map = {}  # Map to store business function ID to testable unit IDs
    tu_id_to_object = {}    # Map to store testable unit ID to the object
    
    # First pass: Load all testable units and map by explicit parentFunctionId
    if os.path.exists(folder_path):
        try:
            # Get list of JSON files in the directory
            json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
            
            # If no files found, the directory may be empty - just continue without testable units
            if not json_files:
                print(f"No JSON files found in: {folder_path} - continuing without testable units")
                return testable_units, testable_unit_map
        except Exception as e:
            print(f"Error accessing testable units folder: {e} - continuing without testable units")
            return testable_units, testable_unit_map
        
        # Process each JSON file
        for filename in json_files:
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, 'r') as f:
                    file_content = json.load(f)
                
                # Check if this is a single testable unit or a collection
                if 'testableUnits' in file_content and isinstance(file_content['testableUnits'], list):
                    # This is a collection file
                    units_collection = file_content['testableUnits']
                    print(f"Found {len(units_collection)} testable units in collection file {filename}")
                    
                    for unit in units_collection:
                        if isinstance(unit, dict):
                            testable_units.append(unit)
                            
                            unit_id = unit.get('id', f"TU-{len(testable_units)}")
                            tu_id_to_object[unit_id] = unit
                            
                            # Look for business function ID in different possible field names
                            business_function_id = unit.get('businessFunctionId', 
                                                unit.get('functionId', 
                                                unit.get('function_id',
                                                unit.get('parentFunctionId'))))
                            
                            if business_function_id:
                                if business_function_id not in testable_unit_map:
                                    testable_unit_map[business_function_id] = []
                                
                                if unit_id not in testable_unit_map[business_function_id]:
                                    testable_unit_map[business_function_id].append(unit_id)
                else:
                    # This is a single unit file
                    testable_units.append(file_content)
                    
                    # Store the unit by ID for lookup
                    if isinstance(file_content, dict):
                        unit_id = file_content.get('id', filename.replace('.json', ''))
                        tu_id_to_object[unit_id] = file_content
                        
                        # Look for business function ID in different possible field names
                        business_function_id = file_content.get('businessFunctionId', 
                                        file_content.get('functionId', 
                                        file_content.get('function_id',
                                        file_content.get('parentFunctionId'))))
                        
                        if business_function_id:
                            if business_function_id not in testable_unit_map:
                                testable_unit_map[business_function_id] = []
                            
                            if unit_id not in testable_unit_map[business_function_id]:
                                testable_unit_map[business_function_id].append(unit_id)
                
                print(f"Successfully processed {filename}")
            except Exception as e:
                print(f"Error reading testable unit file {filename}: {e}")
    else:
        print(f"Testable units folder not found: {folder_path}")
    
    # Print summary
    print(f"Loaded a total of {len(testable_units)} testable units from {folder_path}")
    
    return testable_units, testable_unit_map

def load_all_data(config_path):
    """
    Load all data files required for the report based on a config file.
    
    Args:
        config_path (str): Path to the configuration file
    
    Returns:
        tuple: (sql_code, business_functions, business_process, testable_units, testable_unit_map, output_file_path, output_formats)
    """
    print(f"Reading configuration from: {config_path}")
    
    # Parse the configuration file
    config = parse_config_file(config_path)
    
    # Load the files directly from the provided paths
    sql_code = load_sql_code(config['sql_file_path']) if config['sql_file_path'] else "SQL code file path not provided"
    
    business_functions = load_json_file(
        config['business_functions_path'],
        {"functions": []},
        "business functions"
    ) if config['business_functions_path'] else {"functions": []}
    
    business_process = load_json_file(
        config['business_process_path'],
        {"steps": [], "description": "No business process description available"},
        "business process"
    ) if config['business_process_path'] else {"steps": [], "description": "No business process description available"}
    
    # Load testable units and their initial mapping
    testable_units, testable_unit_map = load_testable_units(config['testable_units_folder']) if config['testable_units_folder'] else ([], {})
    
    # Enhance mapping using business function definitions
    enhance_testable_unit_mapping(business_functions, testable_unit_map)
    
    return sql_code, business_functions, business_process, testable_units, testable_unit_map, config['output_file_path'], config['output_formats']

def enhance_testable_unit_mapping(business_functions, testable_unit_map):
    """
    Enhance the testable unit mapping by examining business functions.
    This adds relationships defined in business functions where TUs are listed.
    
    Args:
        business_functions (dict): The business functions data
        testable_unit_map (dict): The mapping to enhance
    """
    # Extract functions from different possible structures
    functions = []
    if isinstance(business_functions, dict):
        if 'functions' in business_functions:
            functions = business_functions['functions']
        elif 'businessFunctions' in business_functions:
            functions = business_functions['businessFunctions']
    
    # Look for testable units listed in each function
    for function in functions:
        if isinstance(function, dict) and 'id' in function:
            function_id = function['id']
            
            # Look for testable units list with different possible field names
            tu_list = function.get('testableUnits', 
                           function.get('testable_units',
                           function.get('rules', [])))
            
            if tu_list and isinstance(tu_list, list):
                # Ensure this function has an entry in the map
                if function_id not in testable_unit_map:
                    testable_unit_map[function_id] = []
                
                # Add each testable unit to the function's list (if not already there)
                for tu_id in tu_list:
                    if tu_id not in testable_unit_map[function_id]:
                        testable_unit_map[function_id].append(tu_id)