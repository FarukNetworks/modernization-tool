"""
Process Diagram Generator Module

This module is responsible for generating Mermaid flowchart diagrams
that visualize the business process steps and their organization into business functions.
"""

def generate_process_diagram(business_process, business_functions=None):
    """
    Generate a Mermaid flowchart diagram based on the business process with business function grouping.
    
    Args:
        business_process (dict): The business process data containing steps information
        business_functions (dict, optional): The business functions data for grouping steps
    
    Returns:
        str: A Mermaid diagram as a string
    """
    
    mermaid = """```mermaid
flowchart TD
    classDef default fill:#fff,stroke:#000,color:#000
    classDef funcBox fill:#000,stroke:#fff,color:#fff
    classDef stepBox fill:#fff,stroke:#000,color:#000
    classDef decisionBox fill:#ffffcc,stroke:#000,color:#000
    classDef terminalBox fill:#ffcccc,stroke:#000,color:#000
    classDef subgraphStyle fill:#f5f6fbff,stroke:#000,stroke-width:1px
"""
    
    # Function to safely extract steps from various nested structures
    def extract_steps_from_process(process_data):
        steps = []
        
        # Check for businessProcesses structure - this is the structure we found in our file
        if isinstance(process_data, dict) and 'businessProcesses' in process_data and process_data['businessProcesses']:
            # Collect steps from all business processes
            for proc in process_data['businessProcesses']:
                if isinstance(proc, dict) and 'orchestration' in proc and proc['orchestration']:
                    if 'steps' in proc['orchestration'] and proc['orchestration']['steps']:
                        steps.extend(proc['orchestration']['steps'])
        
        # Try other possible structures if the main one didn't work
        if not steps and isinstance(process_data, dict):
            if 'steps' in process_data and process_data['steps']:
                steps = process_data['steps']
            elif 'flow' in process_data and process_data['flow']:
                steps = process_data['flow']
            elif 'processes' in process_data and process_data['processes']:
                steps = process_data['processes']
        
        return steps
    
    # Function to clean text for mermaid compatibility
    def clean_mermaid_text(text):
        if not isinstance(text, str):
            return ""
        # Replace characters that could break mermaid syntax
        text = text.replace('"', "")
        text = text.replace("'", "")
        text = text.replace('|', "/")
        text = text.replace(':', "-")
        text = text.replace('(', "")
        text = text.replace(')', "")
        text = text.replace('{', "")
        text = text.replace('}', "")
        text = text.replace('<', "")
        text = text.replace('>', "")
        text = text.replace('&', "and")
        # Strip any whitespace
        text = text.strip()
        # Don't truncate text, allow full labels
        return text
    
    # Extract steps from the process data
    all_steps = extract_steps_from_process(business_process)
    
    # Sort steps by sequence number if available
    sorted_steps = []
    if all_steps:
        # Try to sort by sequence if available
        sequence_available = all(isinstance(step, dict) and 'sequence' in step for step in all_steps)
        if sequence_available:
            sorted_steps = sorted(all_steps, key=lambda x: x.get('sequence', 0))
        else:
            sorted_steps = all_steps
    
    # Map to store which steps belong to which function
    function_to_steps = {}
    
    # Group steps by business function
    for i, step in enumerate(sorted_steps):
        if isinstance(step, dict) and 'functionId' in step:
            function_id = step['functionId']
            if function_id not in function_to_steps:
                function_to_steps[function_id] = []
            function_to_steps[function_id].append(i)
    
    # Create nodes for all steps
    if sorted_steps:
        # Track decision nodes and their conditions
        decision_nodes = {}
        # Track steps that have decisions
        steps_with_decisions = set()
        # Track terminal steps
        terminal_steps = []
        
        # Map step IDs from JSON to indices
        step_id_map = {}
        for i, step in enumerate(sorted_steps):
            if isinstance(step, dict) and 'id' in step:
                step_id_map[step['id']] = i
        
        # Store the nextStep connections for each step
        # This will help us correctly follow the flow defined in JSON
        step_connections = {}
        for i, step in enumerate(sorted_steps):
            step_id = f"step{i}"
            step_connections[step_id] = None
            
            if isinstance(step, dict) and 'controlFlow' in step:
                control_flow = step.get('controlFlow', {})
                if control_flow.get('type') == 'standard' and 'nextStep' in control_flow:
                    next_step_id = control_flow.get('nextStep')
                    if next_step_id in step_id_map:
                        step_connections[step_id] = f"step{step_id_map[next_step_id]}"
        
        # Phase 1: Create all step nodes first
        for i, step in enumerate(sorted_steps):
            step_id = f"step{i}"
            
            # Get step name based on available fields
            if isinstance(step, dict):
                step_name = step.get('description', 
                             step.get('name',
                             step.get('action',
                             f'Step {i+1}')))
                step_type = step.get('type', '').lower()
            else:
                step_name = f'{step}' if isinstance(step, str) else f'Step {i+1}'
                step_type = ''
            
            # Clean the name for mermaid compatibility
            step_name = clean_mermaid_text(step_name)
            # Add the step number prefix
            step_display_name = f"Step {i+1}: {step_name}"
            
            # Create the step node
            if step_type == 'decision':
                # This is a step that is itself a decision
                mermaid += f"    {step_id}{{{{{step_display_name}}}}}\n"
                mermaid += f"    class {step_id} decisionBox\n"
            elif step_type == 'terminal':
                # Terminal step
                mermaid += f"    {step_id}[[{step_display_name}]]\n"
                mermaid += f"    class {step_id} terminalBox\n"
                terminal_steps.append(step_id)
            else:
                # Regular step
                mermaid += f"    {step_id}[{step_display_name}]\n"
                mermaid += f"    class {step_id} stepBox\n"
            
            # Check for decision control flow
            if isinstance(step, dict) and 'controlFlow' in step:
                control_flow = step.get('controlFlow', {})
                
                if control_flow.get('type') == 'decision' and 'conditions' in control_flow:
                    # Mark this step as having a decision
                    steps_with_decisions.add(step_id)
                    
                    # Create an explicit decision node after this step
                    decision_id = f"{step_id}_decision"
                    
                    # Add the decision diamond
                    mermaid += f"    {decision_id}{{{{Validation Result}}}}\n"
                    mermaid += f"    class {decision_id} decisionBox\n"
                    
                    # Store decision conditions for Phase 3
                    decision_nodes[decision_id] = {
                        'step_id': step_id,
                        'conditions': control_flow.get('conditions', [])
                    }
                
                # Terminal control flow
                elif control_flow.get('type') == 'terminal' or control_flow.get('terminatesExecution', False):
                    terminal_steps.append(step_id)
        
        # Phase 2: Create standard connections between steps based on nextStep values
        for i, step in enumerate(sorted_steps):
            step_id = f"step{i}"
            
            # Skip if this step has a decision or is terminal
            if step_id in steps_with_decisions or step_id in terminal_steps:
                continue
            
            # If we have an explicit nextStep connection, use it
            if step_connections[step_id]:
                next_step_id = step_connections[step_id]
                mermaid += f"    {step_id} --> {next_step_id}\n"
            else:
                # Check if the current step has controlFlow with a standard nextStep
                if isinstance(step, dict) and 'controlFlow' in step:
                    control_flow = step.get('controlFlow', {})
                    if control_flow.get('type') == 'standard' and 'nextStep' in control_flow:
                        next_step = control_flow.get('nextStep')
                        if next_step in step_id_map:
                            next_step_id = f"step{step_id_map[next_step]}"
                            mermaid += f"    {step_id} --> {next_step_id}\n"
                    elif control_flow.get('type') != 'decision' and control_flow.get('type') != 'terminal':
                        # If no specific nextStep, but not a decision or terminal, connect to next sequential step
                        if i + 1 < len(sorted_steps):
                            mermaid += f"    {step_id} --> step{i+1}\n"
                else:
                    # No controlFlow specified, connect to next sequential step
                    if i + 1 < len(sorted_steps):
                        mermaid += f"    {step_id} --> step{i+1}\n"
        
        # Phase 3: Create connections for decision nodes
        for decision_id, info in decision_nodes.items():
            step_id = info['step_id']
            conditions = info['conditions']
            
            # Connect step to its decision node
            mermaid += f"    {step_id} --> {decision_id}\n"
            
            # Create connections for each condition
            for condition in conditions:
                next_step = condition.get('nextStep')
                condition_text = clean_mermaid_text(condition.get('condition', ''))
                
                # Use condition text as the label, since that's what we primarily want to see
                label = condition_text if condition_text else ""
                
                # Find target step ID
                target_id = None
                if next_step in step_id_map:
                    target_id = f"step{step_id_map[next_step]}"
                
                if target_id:
                    # Connect to the target step
                    if label:
                        mermaid += f"    {decision_id} -->|{label}| {target_id}\n"
                    else:
                        mermaid += f"    {decision_id} --> {target_id}\n"
                elif condition.get('terminatesExecution', False):
                    # Create a terminal node
                    counter = len([line for line in mermaid.split('\n') if "terminalBox" in line]) + 1
                    term_id = f"{decision_id}_term_{counter}"
                    
                    # Get terminal description
                    desc = clean_mermaid_text(condition.get('returnsDescription', 'Process terminates'))
                    
                    # Create terminal node and connection
                    mermaid += f"    {term_id}[[{desc}]]\n"
                    mermaid += f"    class {term_id} terminalBox\n"
                    if label:
                        mermaid += f"    {decision_id} -->|{label}| {term_id}\n"
                    else:
                        mermaid += f"    {decision_id} --> {term_id}\n"
        
        # Phase 4: Create terminal nodes for steps with terminal control flow
        for i, step in enumerate(sorted_steps):
            step_id = f"step{i}"
            
            if isinstance(step, dict) and 'controlFlow' in step:
                control_flow = step.get('controlFlow', {})
                
                if (control_flow.get('type') == 'terminal' or 
                    control_flow.get('terminatesExecution', False)) and step_id in terminal_steps:
                    # Create terminal node
                    term_id = f"{step_id}_end"
                    
                    # Get terminal description
                    desc = clean_mermaid_text(control_flow.get('returnsDescription', 'Process completes'))
                    
                    # Create terminal node and connection
                    mermaid += f"    {term_id}[[{desc}]]\n"
                    mermaid += f"    class {term_id} terminalBox\n"
                    mermaid += f"    {step_id} --> {term_id}\n"
        
        # Phase 5: Add function boxes and connect to their steps
        if business_functions and isinstance(business_functions, dict):
            # Extract functions list
            functions = []
            if 'functions' in business_functions:
                functions = business_functions['functions']
            elif 'businessFunctions' in business_functions:
                functions = business_functions['businessFunctions']
            
            # Add function boxes on the left
            for function in functions:
                if isinstance(function, dict) and 'id' in function:
                    function_id = function['id']
                    if function_id in function_to_steps and function_to_steps[function_id]:
                        function_name = function.get('name', function_id)
                        # Clean function name for Mermaid compatibility
                        function_name = clean_mermaid_text(function_name)
                        
                        # Sanitize function_id for Mermaid compatibility
                        safe_function_id = function_id.replace('-', '_').replace('.', '_')
                        
                        # Create function box
                        mermaid += f"    {safe_function_id}[{function_id}: {function_name}]\n"
                        mermaid += f"    class {safe_function_id} funcBox\n"
                        
                        # Get step indices for this function
                        step_indices = function_to_steps[function_id]
                        
                        # Connect function box to first step of this function
                        if step_indices:
                            first_step = f"step{step_indices[0]}"
                            mermaid += f"    {safe_function_id} --> {first_step}\n"
                            
                            # Group steps for this function with a styled subgraph
                            safe_group_id = f"{safe_function_id}_group"
                            mermaid += f"    subgraph {safe_group_id}[\" \"]\n"
                            for step_idx in step_indices:
                                mermaid += f"        step{step_idx}\n"
                            mermaid += "    end\n"
                            mermaid += f"    class {safe_group_id} subgraphStyle\n"
    else:
        # No steps found in any format
        mermaid += "    noProcess[No business process steps available]\n"
    
    mermaid += "```"
    return mermaid
