from google.genai import types
import json
import os

available_repository_methods = [
    "public override async Task<TEntity?> GetByIdAsync(object id)",
    "public override async Task<IEnumerable<TEntity>> GetAllAsync()",
    "public override async Task<IEnumerable<TEntity>> FindAsync(Expression<Func<TEntity, bool>> predicate)",
    "public override async Task<IEnumerable<TEntity>> FindAsync(Expression<Func<TEntity, bool>> predicate, params Expression<Func<TEntity, object>>[] includeProperties)",
    "public override async Task<bool> AnyAsync(Expression<Func<TEntity, bool>> predicate)",
    "public override async Task<int> CountAsync(Expression<Func<TEntity, bool>>? predicate = null)",
    "public override async Task<TEntity?> FirstOrDefaultAsync(Expression<Func<TEntity, bool>> predicate)",
    "public override IQueryable<TEntity> GetQueryable(params Expression<Func<TEntity, object>>[] includeProperties)",
    "public virtual async Task<TEntity> AddAsync(TEntity entity)",
    "public virtual async Task<IEnumerable<TEntity>> AddRangeAsync(IEnumerable<TEntity> entities)",
    "public virtual async Task<TEntity> UpdateAsync(TEntity entity)",
    "public virtual async Task<IEnumerable<TEntity>> UpdateRangeAsync(IEnumerable<TEntity> entities)",
    "public virtual async Task<bool> DeleteAsync(TEntity entity)",
    "public virtual async Task<bool> DeleteAsync(object id)",
    "public virtual async Task<bool> DeleteRangeAsync(IEnumerable<TEntity> entities)",
    "public async Task<int> SaveChangesAsync()",
]


def get_prompt(procedure_name, procedure_definition, project_path):
    """
    Generate prompt for implementation execution

    Args:
        procedure_name: Name of the procedure
        procedure_definition: SQL code of the procedure
        project_path: Project path

    Returns:
        Prompt for the agent
    """
    # Get business analysis results
    business_rules_json = os.path.join(
        project_path,
        "analysis",
        procedure_name,
        f"{procedure_name}_business_rules.json",
    )

    business_functions_json = os.path.join(
        project_path,
        "analysis",
        procedure_name,
        f"{procedure_name}_business_functions.json",
    )

    business_processes_json = os.path.join(
        project_path,
        "analysis",
        procedure_name,
        f"{procedure_name}_business_processes.json",
    )

    # Get implementation plan
    implementation_plan_path = os.path.join(
        project_path,
        "analysis",
        procedure_name,
        f"{procedure_name}_implementation_plan.json",
    )
    implementation_plan = {}
    if os.path.exists(implementation_plan_path):
        try:
            with open(implementation_plan_path, "r") as f:
                implementation_plan = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load implementation plan: {str(e)}")

    # Format the prompt
    prompt = f"""
You are a senior C# developer tasked with executing the implementation plan for a SQL stored procedure.

## Stored Procedure Information
```sql
{procedure_definition}
```

## Business Analysis
```json
{json.dumps(business_rules_json, indent=2)}
{json.dumps(business_functions_json, indent=2)}
{json.dumps(business_processes_json, indent=2)}
```

## Implementation Plan
```json
{json.dumps(implementation_plan, indent=2)}
```

## Your Task
Based on the implementation plan, create the necessary C# implementation files.

Focus on executing the implementation plan accurately. Generate all necessary files including:
1. Service classes
2. Data models
3. Repository interfaces and implementations
4. Unit tests
5. Any other files needed for a complete implementation

Your code should follow best practices:
- Clean architecture principles
- SOLID principles
- Proper dependency injection
- Error handling
- Async/await for database operations
- Meaningful comments
- Unit test coverage

Please provide the complete implementation code for all required files. 
Read any files that are needed to be created and implement them.
"""

    return prompt
