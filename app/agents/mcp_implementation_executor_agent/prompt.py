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
        f"business_rules.json",
    )

    business_functions_json = os.path.join(
        project_path,
        "analysis",
        procedure_name,
        f"business_functions.json",
    )

    business_processes_json = os.path.join(
        project_path,
        "analysis",
        procedure_name,
        f"business_processes.json",
    )

    # Get implementation plan
    implementation_plan_path = os.path.join(
        project_path,
        "analysis",
        procedure_name,
        f"implementation_plan.json",
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
<behavior_rules> You have one mission: execute exactly what is requested. Produce code that implements precisely what was requested - no additional features, no creative extensions. Follow instructions to the letter. Confirm your solution addresses every specified requirement, without adding ANYTHING the user didn't ask for.
</behavior_rules>

<most_relevant_source_of_truth>
Implementation plan: 
{json.dumps(implementation_plan, indent=2)}

Implementation plan is the reference for the coding execution. Use that file to set up the project structure and coding execution. All other files are secondary and are for reference only and specific local context.
</most_relevant_source_of_truth>


# Task: SQL Stored Procedure to C# Migration

## Overview
Implement a migration of a SQL stored procedure to C# within our existing .NET 9 API, adhering to the repository pattern. The following information sources are provided:

1.  The original SQL stored procedure (reference) - [{procedure_definition}]
2.  Entity Framework Core analysis:
    **This analysis contains information about dependencies already created in the project using the scaffold command. Models and DbContext details are in the JSON file:**
    - [READ: analysis/{procedure_name}/ef_analysis.json]
3.  Use the `sql2code` namespace.
4.  Each model has its own repository inheriting from the base repository. Extend individual repositories in the Repositories folder as needed.

Repository abstraction paths: 
[READ: {project_path}/csharp-code/Abstractions/Repositories/Repository.cs]
[READ: {project_path}/csharp-code/Abstractions/Repositories/IRepository.cs]
[READ: {project_path}/csharp-code/Abstractions/Repositories/IReadRepository.cs]
[READ: {project_path}/csharp-code/Abstractions/Repositories/IWriteRepository.cs]

**This is the path to available repository methods: [{available_repository_methods}]**

**This is the path to model files content: [READ: {project_path}/csharp-code/Models/]**


**Project packages:**
Project 'sql2code' has the following package references
   [net9.0]: 
   Top-level Package                               Requested   Resolved
   > Microsoft.AspNetCore.OpenApi                  9.0.4       9.0.4   
   > Microsoft.Data.SqlClient                      6.0.1       6.0.1   
   > Microsoft.EntityFrameworkCore                 9.0.4       9.0.4   
   > Microsoft.EntityFrameworkCore.Design          9.0.4       9.0.4   
   > Microsoft.EntityFrameworkCore.InMemory        9.0.4       9.0.4   
   > Microsoft.EntityFrameworkCore.Relational      9.0.4       9.0.4   
   > Microsoft.EntityFrameworkCore.SqlServer       9.0.4       9.0.4   
   > Microsoft.NET.Test.Sdk                        17.13.0     17.13.0 
   > Moq                                           4.20.72     4.20.72 
   > Moq.EntityFrameworkCore                       9.0.0.1     9.0.0.1 
   > Newtonsoft.Json                               13.0.3      13.0.3  
   > Swashbuckle.AspNetCore                        8.1.1       8.1.1   
   > xUnit                                         2.9.3       2.9.3   
   > xunit.runner.visualstudio                     3.0.2       3.0.2   

## .NET Migration Requirements

- Implement using standard .NET best practices for repository pattern, Entity Framework Core, and ASP.NET Core within an ASP.NET Core application
- Implement components in the dependency order specified in the task list, ensuring smooth integration
- Achieve strict feature parity; the final functional outcome must precisely match the original stored procedure's behavior
- Focus on replicating the existing logic across the layers defined in the `implementation_approach` JSON, without introducing any additional features
- Adhere strictly to the layered architecture and component responsibilities as defined in the `implementation_approach` JSON; the JSON plan dictates the structure and logic placement
- Refactor business logic into methods where applicable, leveraging existing test specifications to ensure correctness
- Provide detailed XML documentation, with references to relevant business logic files and corresponding SQL code, whenever possible and reasonable
- Implement robust error handling and logging throughout the application to facilitate debugging and maintenance
- Conduct thorough unit testing and integration testing to validate the correctness and stability of each component after implementation
- Optimize data access patterns for efficiency, ensuring minimal overhead while maintaining data integrity and consistency
- Secure the application against common web vulnerabilities, such as SQL injection and cross-site scripting (XSS)
- Follow secure coding practices, including input validation and output encoding, to mitigate potential risks


## Implementation Instructions

1.  Carefully review the provided task list detailing each component to be implemented, paying close attention to the responsibilities and logic placement assigned to each layer, as outlined in the `implementation_approach` JSON plan.
2.  Implement each component in dependency order, strictly adhering to the architectural layering and logic placement defined in the JSON plan to maintain separation of concerns.
3.  For each implementation, comprehensively explain your design decisions, especially regarding complex patterns or algorithms, ensuring clarity and maintainability.
4.  Employ standard Entity Framework Core and LINQ patterns for robust and efficient data access, optimizing query performance where appropriate.
5.  Ensure that error handling and transaction boundaries precisely mirror the behavior of the original stored procedure to maintain data integrity and consistency.
6.  Develop comprehensive unit tests for each component as specified, achieving high code coverage and thoroughly validating functionality.
7.  Incorporate detailed XML documentation comments, specifically referencing:

    *   The corresponding business rules (BR-XXX), primarily within Services/Domain Services layer comments where these rules are enforced and orchestrated.
    *   Related business functions (BF-XXX), chiefly in Controller/Services layer comments, to indicate the initiation or implementation of each function.
    *   The specific SQL code sections being translated, included as comments within the layer where the equivalent C# logic is implemented, as dictated by the JSON plan (e.g., simple SELECT statements in Repository, complex logic/aggregation in Services/Mappers).
    *   The relevant sections of the original stored procedure, used judiciously to clarify implementation choices in the appropriate layer according to the JSON plan.
    *   Critically, Repository method comments should reference only simple, direct SQL equivalents (such as basic SELECT/WHERE clauses implemented in that method) and must not reference complex business rules or multi-step SQL logic sections that are implemented in higher layers per the JSON plan.

    After completing this section, verify progress before continuing.


## Implementation Approach

- Utilize LINQ expressions for standard SQL query operations.
- For complex SQL patterns (e.g., PIVOT, dynamic SQL), implement equivalent C# logic within the Application Services, Domain Services, or Mapper layers as specified in the `implementation_approach` JSON plan. Repositories should remain simple data retrieval components, implementing only basic query operations as defined in the plan.
- Maintain transaction boundaries identical to the original stored procedure.
- Preserve the existing error handling and status reporting mechanisms.
- Ensure all data modifications and side effects are accurately implemented.

Implement the components step-by-step according to the task list. For each component, provide the complete C# implementation with comprehensive XML documentation. Maintain exact feature parity (in terms of functional outcome) with the original stored procedure, implementing the logic according to the provided JSON plan, without introducing new features. Validate each component after implementation to confirm functional equivalence.

Provide an additional file, Extensions/{procedure_name}/Extensions.cs, containing the builder registration for all required services, repositories, mappers, and other dependencies, within a method.

```csharp
// Extensions/{procedure_name}/Extensions.cs
public static class {procedure_name}Extensions
{{
    public static IServiceCollection Add{procedure_name}_Services(this IServiceCollection services, IConfiguration configuration)
    {{
        // [ADD BUILDER REGISTRATION FOR REPOSITORY, DOMAIN SERVICES, MAPPERS, APPLICATION SERVICES, AND EVERYTHING ELSE NEEDED]
        return services;
    }}
}}
``` 

Given the existing Models folder and DbContext at /csharp-code/Data/AppDbContext.cs, generate the service and API layers for a new procedure. Follow these specifications:

*Service Layer*
Create the service layer within the Services/{procedure_name} folder. The primary business logic should reside in a single file with interface file.

*API Layer*
Construct the API layer within the Controllers folder. Create a Controller folder Controllers/{procedure_name} and create a Controller file inside it.

<important_rules>
<rule>
Do not generate any of the following files: [Program.cs, sql2code.csproj, appsettings.json].
</rule>
<rule>
Do not create any test folders or testing files.
</rule>
<rule>
The DbContext and models have already been created using the dotnet scaffold command.
</rule>
<rule>
Use plural names for all folders (e.g., Services, Repositories, Controllers).
</rule>
</important_rules>

When implementing LINQ queries with Entity Framework Core, be aware of these translation limitations and follow the best practices outlined below. The goal is to optimize query performance by minimizing client-side evaluation and ensuring that as much processing as possible is done on the server. Provide complete, runnable C# code examples demonstrating both the problematic patterns and the recommended solutions. Include Entity Framework Core setup (DbContext, entity definitions) and seed data.

1.  **Materialization Considerations:**
    *   `DateOnly.ToDateTime()`: Always materialize using `.ToList()` or `.AsEnumerable()` before applying this conversion. Show a complete example.
    *   `TimeOnly` Operations: Most `TimeOnly` operations require client-side evaluation. Provide examples showing the limitations and correct usage.
    *   Custom C# Methods: Custom C# methods cannot be directly translated to SQL. Demonstrate this limitation with a custom method example.
    *   Complex String Manipulation: Use simple string conditions within the query and perform more complex manipulations in memory after materialization. Include a performance comparison.
    *   Complex Collection Operations: Perform basic filtering in SQL, then execute complex collection operations in memory. Show how to optimize this pattern.

2.  **Query Patterns to Avoid:**
    *   Mixing Client and Server Evaluation: Avoid mixing client and server evaluation within a single query. Provide a clear example demonstrating the issue and a refactored solution.
    *   `.Contains()` on In-Memory Collections: Avoid using `.Contains()` on in-memory collections in `WHERE` clauses. Show a more efficient approach using `AsQueryable()`.
    *   Capturing Local Variables: Be cautious when capturing local variables in complex ways within queries, as this can lead to unexpected behavior. Give an example of a problematic scenario and a safer alternative.
    *   Complex Type Conversions: Avoid complex type conversions within queries, as they might not be supported by the database provider. Provide code illustrating this issue.

3.  **Recommended Patterns:**
    *   `DateOnly`/`TimeOnly`: Query using direct comparisons first, then convert after materialization. Show the complete before-and-after code.
    *   Complex Operations: Split queries into simple database queries and in-memory processing for complex operations. Demonstrate a real-world scenario.
    *   Grouping with Complex Calculations: Fetch raw data and perform grouping in memory for complex calculations. Include a performance assessment.
    *   Joining with Complex Logic: Use multiple simple queries and join the results in memory when dealing with complex join logic. Show how to optimize this pattern.

4.  **Proper Query Structure (with complete, runnable code):**

    ```csharp
    // GOOD: Materialize first, then perform non-translatable operations
    var result = dbContext.Entities
        .Where(e => e.SomeProperty == someValue)
        .ToList() // Materialize here
        .Select(e => new
        {{
            Id = e.Id,
            ConvertedDate = e.DateOnlyField.ToDateTime(TimeOnly.MinValue)
        }}).ToList();

    // BAD: Trying to use non-translatable methods in the query
    // (This will fail during translation)
    /*
    var result = dbContext.Entities
        .Where(e => e.SomeProperty == someValue)
        .Select(e => new
        {{
            Id = e.Id,
            ConvertedDate = e.DateOnlyField.ToDateTime(TimeOnly.MinValue) // Will fail
        }}).ToList();
    */
    ```

    Provide a complete, compilable code example, including:

    *   Entity definitions with `DateOnly` and `TimeOnly` properties.
    *   DbContext setup.
    *   Seed data.
    *   Both the correct and incorrect query examples, properly commented.

Provide complete, executable code for each scenario, including comprehensive comments explaining the reasoning behind each approach and potential pitfalls. Implement benchmarks to quantify the performance improvements of the recommended patterns. Ensure that all code is compatible with the latest version of Entity Framework Core. After completing each section, verify progress before continuing to ensure clarity and correctness.

All the procedures new files should be created in the folder with the procedure name {procedure_name}. So all the folders will look like this: 
- Controllers/{procedure_name}
- Services/{procedure_name}
- Extensions/{procedure_name}
- DTOs/{procedure_name}
"""

    return prompt
