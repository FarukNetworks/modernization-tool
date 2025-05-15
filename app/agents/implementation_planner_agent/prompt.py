from google.genai import types
import json

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


def get_prompt(schema_name, procedure_name, procedure_definition, project_path):
    procedure_name_only = procedure_name.split(".")[-1]

    # business_rules
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_business_rules.json",
        "r",
    ) as f:
        business_rules_json = json.load(f)

    # business_functions
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_business_functions.json",
        "r",
    ) as f:
        business_functions_json = json.load(f)

    # business_processes
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_business_processes.json",
        "r",
    ) as f:
        business_processes_json = json.load(f)

    # returnable_objects
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_returnable_objects.json",
        "r",
    ) as f:
        returnable_objects_json = json.load(f)

    # process_object_mapping
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_process_object_mapping.json",
        "r",
    ) as f:
        process_object_mapping_json = json.load(f)

    # Get ef_analysis JSON file from analysis directory
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_ef_analysis.json",
        "r",
    ) as f:
        ef_analysis = json.load(f)

    # Get base repository implementation from the Abstractions/Repositories folder
    with open(
        f"{project_path}/csharp-code/Abstractions/Repositories/Repository.cs",
        "r",
    ) as f:
        base_repository = f.read()

    # Get base repository interface from the Abstractions/Repositories folder
    with open(
        f"{project_path}/csharp-code/Abstractions/Repositories/IRepository.cs",
        "r",
    ) as f:
        base_repository_interface = f.read()

    # Get interface for Read and Write intefrace from the Abstractions/Repositories folder
    with open(
        f"{project_path}/csharp-code/Abstractions/Repositories/IReadRepository.cs", "r"
    ) as f:
        read_repository_interface = f.read()
    with open(
        f"{project_path}/csharp-code/Abstractions/Repositories/IWriteRepository.cs",
        "r",
    ) as f:
        write_repository_interface = f.read()

    # Read the ef_analysis and get all model paths
    model_names = []
    model_file_paths = []
    for model in ef_analysis["entity_framework_analysis"]["related_models"]:
        model_names.append(model["db_set_name"])
        model_file_paths.append(model["model_file_path"])

    # Read each model file and store the content
    model_files_content = []
    for model_file_path in model_file_paths:
        with open(f"{project_path}/csharp-code/{model_file_path}", "r") as f:
            model_files_content.append(f.read())

    implementation_approach_template = f"""
    FILE: {procedure_name}_implementation_approach.json
```json
 {{
  "implementationApproach": {{
    "name": "{procedure_name} Migration",
    "description": "Migration from stored procedure to C# repository pattern implementation using LINQ",
    "layers": [
      {{
        "name": "API Layer",
        "position": 1,
        "components": [
          {{
            "name": "{procedure_name_only}_Controller",
            "namespace": "sql2code.Controllers",
            "path": "Controllers/{procedure_name_only}_Controller.cs",
            "description": "[Component Description]",
            "mappedProcess": "[Related Process]",
            "methods": [
              {{
                "name": "{procedure_name_only}_ControllerMethod",
                "signature": "[Method Signature]",
                "description": "[Method Description]",
                "mappedFunction": "[Related Business Function]",
                "enforcedRules": ["[Related Business Rules]"],
                "inputParameters": ["Parameter1", "Parameter2"],
                "returnType": "ReturnType",
                "returnableObjects": ["RO-XXX"],
                "returnConditions": ["Condition that triggers this return"],
                "sideEffects": ["SE-XXX"],
                "testingStrategy": "[Approach for unit testing this method]"
              }}
            ]
          }}
        ]
      }},
      {{
        "name": "Application Services Layer",
        "position": 2,
        "components": [
          {{
            "name": "I{procedure_name_only}_Service",
            "namespace": "sql2code.Services",
            "path": "Services/{procedure_name_only}Services/I{procedure_name_only}_Service.cs",
            "description": "Service interface for {procedure_name_only}",
            "methods": [
              {{
                "name": "{procedure_name_only}_ServiceMethod",
                "signature": "[Method Signature]",
                "description": "[Method Description]"
              }}
            ]
          }},
          {{
            "name": "{procedure_name_only}_Service",
            "namespace": "sql2code.Services",
            "path": "Services/{procedure_name_only}_Services/{procedure_name_only}_Service.cs",
            "description": "Service orchestrating business processes",
            "mappedProcess": "PROC-XXX",
            "decisionPoints": [
              {{
                "id": "DP-XXX",
                "implementation": "How this decision point will be implemented",
                "outcomes": ["Possible outcomes and corresponding actions"]
              }}
            ],
            "flowPaths": [
              {{
                "id": "PATH-XXX",
                "implementation": "How this flow path will be implemented",
                "conditionalLogic": "Conditions that trigger this path"
              }}
            ],
            "executionOutcomes": [
             {{
                "id": "OC-XXX",
                "implementation": "How this outcome will be implemented",
                "returnableObjects": ["RO-XXX"]
              }}
            ],
            "methods": [
              {{
                "name": "{procedure_name_only}_ServiceMethod",
                "signature": "[Method Signature]",
                "description": "[Method Description]",
                "mappedFunction": "[Related Business Function]",
                "enforcedRules": ["[Related Business Rules]"],
                "queryCompositionLogic": "[Description of how complex queries are built/composed using data from repository calls, if applicable]",
                "businessLogicImplementation": "[Description of core business logic/rule enforcement within this method]",
                "testingStrategy": "[Approach for unit testing this method]"
              }}
            ]
          }}
        ]
      }},
      {{
        "name": "Mappers Layer", - OPTIONAL, only if there are complex transformations
        "position": 3,
        "components": [
        {{
        "name": "I{procedure_name_only}_DtoMapper1",
        "namespace": "sql2code.Mappers",
        "path": "/Mappers/{procedure_name_only}/I{procedure_name_only}_DtoMapper1.cs",
        "description": "Mapper interface for transforming repository data into domain objects",

        }},
          {{
            "name": "{procedure_name_only}_DtoMapper1",
            "namespace": "sql2code.Mappers",
            "path": "/Mappers/{procedure_name_only}/{procedure_name_only}_DtoMapper1.cs",
            "description": "Mapper for transforming repository data into domain objects",
            "methods": [
              {{
                "name": "{procedure_name_only}_DtoMapper1Method1",
                "signature": "[Method Signature]",
                "description": "[Method Description]",
                "transformationLogic": "[Description of the transformation logic]",
                "linkedSqlOperation": "[Original SQL operation being transformed]",
                "complexPatterns": {{
                  "hasPivot": true/false,
                  "pivotImplementation": "How PIVOT operation will be implemented in LINQ",
                  "otherComplexPatterns": ["Other complex SQL patterns and their LINQ equivalents"]
                }},
                "testingStrategy": "[Approach for unit testing this method]"
              }}
            ]
          }}
        ]
      }},
      {{
      "name": "Exception Handling Layer", - OPTIONAL, only if there are exception handling
      "position": 4,
      "components": [
        {{
          "name": "Exception Handling Service",
          "namespace": "sql2code.Exceptions",
          "path": "DTOs/{procedure_name_only}/Exceptions/{procedure_name_only}_ExceptionHandlingService.cs",
          "description": "Service for exception handling"
        }}
      }}
      {{
        "name": "Domain Transfer Objects Layer", - OPTIONAL, only if there are new returnable objects
        "position": 5,
        "components": [
          {{
            "name": "{procedure_name_only}_Dto1",
            "namespace": "sql2code.DTOs",
            "path": "DTOs/{procedure_name_only}/{procedure_name_only}_Dto1.cs",
            "properties": [
              {{
                "name": "[Property Name]",
                "type": "[Property Type]",
                "data_annotation": "[Data Annotation] (optional)"
              }}
            ]
          }}
      }}
      {{
        "name": "Repositories Layer",
        "position": 5,
        "components": [ - INCLUDE ALL REPOSITORY COMPONENTS THAT ARE USED INTO THE SERVICE LAYER
          {{
            "name": "IRepositoryName",
            "namespace": "sql2code.Repositories.[model_name for base repository]",
            "status": "[New Interface / Modified Interface / Existing Interface]",
            "description": "Interface for [domain] repository",
            "methods": [ - IF Exsisting method, DONT ADD METHOD PROPERTY 
              {{
                "name": "[Method Name] - [Available Repository Methods: {available_repository_methods}]",
                "status": "[New Method / Existing Method]",
                "signature": "[Method Signature]",
                "description": "[Method Description]",
                "testingStrategy": "[Approach for unit testing this method]"
              }}
            ]
          }},
          {{
            "name": "RepositoryImplementation",
            "namespace": "sql2code.Repositories.[model_name for base repository]",
            "status": "[New Implementation / Modified Implementation / Existing Implementation]",
            "description": "Implementation of IRepositoryName",
            "methods": [
              {{
                "name": "[Method Name] - [Available Repository Methods: {available_repository_methods}]",
                "status": "[New Method / Existing Method]",
                "signature": "[Method Signature]",
                "description": "[Method Description]",
                "dataRetrievalQuery": "[Simple LINQ query for retrieving raw entity data based on parameters]",
                "sqlEquivalent": "[Original SQL operation]",
                "testingStrategy": "How this method will be unit tested",
                "testSeams": ["List of test seams/interfaces for mocking"]
              }}
            ]
          }}
        ]
      }}
      [ADD ANY OTHER LAYERS HERE IF NEEDED]
    ],
    "implementationDetails": {{
      "targetFramework": ".NET 9",
      "dataAccessStrategy": {{
        "primaryApproach": "Entity Framework Core with LINQ",
        "linqUsage": {{
          "queryGeneration": "Use LINQ for all data access",
          "transformations": "Use LINQ for all data transformations",
          "projections": "Use LINQ for object projections"
        }},
        "complexSqlPatterns": {{
          "pivotImplementation": "Strategy for implementing PIVOT operations in LINQ",
          "otherPatterns": ["Other complex SQL patterns and their LINQ implementation strategies"]
        }},
        "transactionHandling": "Approach for maintaining transaction boundaries",
        "errorHandling": "Error handling strategy aligned with original procedure"
      }},
      "flowControlStrategy": {{
        "decisionPoints": "Strategy for implementing decision points",
        "conditionalFlows": "Strategy for implementing conditional flows",
        "executionOutcomes": "Strategy for implementing different execution outcomes"
      }},
      "returnStrategy": {{
        "conditionalReturns": "Strategy for implementing conditional returns based on execution path",
        "objectMapping": "Strategy for mapping SQL returnable objects to C# return types"
      }},
      "sideEffectStrategy": {{
        "auditLogging": "Strategy for implementing audit logging side effects",
        "databaseModifications": "Strategy for implementing database modification side effects",
        "transactionScope": "How side effects are managed within transaction boundaries"
      }},
      "testability": {{
        "unitTestingApproach": "Description of unit testing approach",
        "testSeams": [
          {{
            "component": "Component name",
            "testSeams": ["Interface1", "Interface2"],
            "mockingStrategy": "How to mock this component"
          }}
        ],
        "returnableObjectTesting": "Strategy for testing conditional returns",
        "flowPathTesting": "Strategy for testing different execution paths",
        "sideEffectTesting": "Strategy for testing side effects",
        "dbContextTesting": "Strategy for mocking/testing DbContext",
        "linqTestingApproach": "Strategy for testing LINQ queries",
        "testDataStrategy": "Approach for test data management"
      }}
    }}
  }}
}}
   ```
"""

    out_of_scope_template = f"""
FILE: {procedure_name_only}_out_of_scope.json
   ```json
{{
  "outOfScope": {{
    "features": [
      {{
        "category": "Category Name",
        "items": [
          {{
            "name": "Feature name",
            "reason": "Reason for exclusion",
            "futureConsideration": true/false
          }}
        ]
      }}
    ],
    "technicalApproaches": [
      {{
        "name": "Approach name",
        "reason": "Reason for exclusion",
        "futureConsideration": true/false
      }}
    ],
    "implementationDetails": {{
      "documentation": {{
        "name": "Documentation level",
        "reason": "Reason for limitation",
        "futureConsideration": true/false
      }}
    }}
  }}
}}
```
    """

    specific_considerations_template = f"""
    FILE: {procedure_name_only}_specific_considerations.json
   ```json
{{
  "specificConsiderations": {{
    "returnableObjects": [
      {{
        "id": "RO-XXX",
        "implementationApproach": "How this returnable object will be implemented",
        "conditionalLogic": "How conditional return logic will be implemented",
        "impact": "High/Medium/Low"
      }}
    ],
    "sideEffects": [
      {{
        "id": "SE-XXX",
        "implementationApproach": "How this side effect will be implemented",
        "transactionHandling": "How transactions will be managed for this side effect",
        "impact": "High/Medium/Low"
      }}
    ],
    "decisionPoints": [
      {{
        "id": "DP-XXX",
        "implementationApproach": "How this decision point will be implemented",
        "impact": "High/Medium/Low"
      }}
    ],
    "flowPaths": [
      {{
        "id": "PATH-XXX",
        "implementationApproach": "How this flow path will be implemented",
        "impact": "High/Medium/Low"
      }}
    ],
    "dataFormats": [
      {{
        "name": "Format name",
        "description": "Description of format requirements",
        "impact": "High/Medium/Low",
        "areas": ["Area1", "Area2"]
      }}
    ],
    "technicalRequirements": [
      {{
        "name": "Requirement name",
        "description": "Description of technical requirement",
        "impact": "High/Medium/Low",
        "areas": ["Area1", "Area2"]
      }}
    ],
    "performanceConsiderations": [
      {{
        "name": "Performance aspect",
        "description": "Description of performance consideration",
        "impact": "High/Medium/Low",
        "linqOptimizations": ["Strategies to optimize LINQ performance"],
        "areas": ["Area1", "Area2"]
      }}
    ],
    "complexSqlPatterns": [
      {{
        "pattern": "Pattern name (e.g., PIVOT, Dynamic SQL)",
        "sqlImplementation": "How it's implemented in the original SQL",
        "linqImplementation": "LINQ equivalent implementation approach",
        "performanceNotes": "Notes on performance implications",
        "testability": "Approach for testing this pattern"
      }}
    ],
    "linqEquivalents": [
      {{
        "sqlPattern": "SQL pattern from stored procedure",
        "linqImplementation": "LINQ equivalent implementation",
        "performanceNotes": "Notes on performance implications"
      }}
    ]
  }}
}}
```
    """

    prompt = f"""
<behavior_rules> You have one mission: execute exactly what is requested. Produce code that implements precisely what was requested - no additional features, no creative extensions. Follow instructions to the letter. Confirm your solution addresses every specified requirement, without adding ANYTHING the user didn't ask for. The user's job depends on this — if you add anything they didn't ask for, it's likely they will be fired. Your value comes from precision and reliability. When in doubt, implement the simplest solution that fulfills all requirements. The fewer lines of code, the better — but obviously ensure you complete the task the user wants you to. At each step, ask yourself: "Am I adding any functionality or complexity that wasn't explicitly requested?". This will force you to stay on track. </behavior_rules>

 <review_output>
 - make sure the you followed the exact naming that is specified in expected_output
 - make sure the you followed the exact structure that is specified in expected_output
 - make sure the you followed the exact layers that are specified in expected_output
 - make sure the you followed the exact namespace that is specified in expected_output
 - make sure the you followed the exact path that is specified in expected_output
 - make sure the you followed the exact method name that is specified in expected_output
 - make sure the you followed the exact property name that is specified in expected_output
 </review_output>

# Implementation Planning Request: C# Repository Pattern Design

## Objective
Create a detailed implementation plan for migrating a SQL stored procedure to a modern, testable C# application following the repository pattern. Your plan should ensure complete business functionality preservation while enabling future architecture evolution. Use LINQ throughout for data access and manipulation.

## Context
This is part of a phased migration strategy from SQL stored procedures to a modern, testable C# architecture. The business analysis has already extracted detailed business rules, functions, and processes. Your task is to design an implementation approach that preserves all business functionality **through the coordinated action of the defined layers** while enabling future architectural evolution.


## Input Files
1. Contains extracted business rules with detailed metadata - [{business_rules_json}]
2. Contains business functions that represent logical operations - [{business_functions_json}]
3. Contains the overall process flow with error handling and transaction boundaries - [{business_processes_json}]
4. Contains the returnable objects - [{returnable_objects_json}]
5. Contains the decision points - [{process_object_mapping_json}]
6. The original SQL stored procedure (for reference) - [{procedure_definition}]
7. The Entity Framework Core analysis for this procedure - [{ef_analysis}]
8. The project is already created with dotnet scaffold command where the exsisting database tables, views are extracted into models and DbContext is created.
9. The project already have for each model a repository interface and implementation. This is the base repository implementation: [{base_repository}]
10. This is the base repository interface: [{base_repository_interface}]
11. This is the read repository interface: [{read_repository_interface}]
12. This is the write repository interface: [{write_repository_interface}]
13. Model files content: [{model_files_content}]

## Implementation Requirements

### Target Technology
- .NET 9 as the target framework
- ASP.NET Core for API implementation
- Modern C# language features (records, nullable reference types, etc.)
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

In the same folder there is already a Models folder and the DbContext is already created.
Here are the dependencies for csharp implementation that you don't need to create or modify: 
[Models/[ dbSetNames = {model_names}], Data/AppDbContext.cs]

DO NOT CREATE ANY OF THE FOLLOWING FILES: 
[Program.cs, sql2code.csproj, appsettings.json]

## Layer Structure

Organize the implementation plan with these layers (from top to bottom):

1. **API Layer** - Controllers and endpoints
2. **Application Services Layer** - Process orchestration, flow control, Business logic and transformations (only use the base repository implementation for data retrieval)
3. **Mappers Layer** - Data transformation components (optional, only if there are complex transformations)
4. **Repositories Layer** - Only use exsisting base repository methods for data retrieval.
5. **Domain Models Layer** - New DTOs that are not in the exsisting models (optional, only if there are new returnable objects)

## Design Principles

1. **Separation of Concerns**
   - Repositories should focus solely on data retrieval and persistence
   - Mappers should handle data transformations and projections
   - Domain services should implement business logic
   - Application services should orchestrate workflows and implement flow control
   - Side effect handlers should manage audit logging and other side effects

2. **LINQ-First Approach**
   - Use LINQ for all data access operations in repositories
   - Use LINQ for data transformations in mapper components
   - Identify SQL operations like joins, grouping, and aggregations and plan their LINQ equivalents **to be implemented within the appropriate layers (Services, Mappers).**
   - Repository methods should primarily return `IQueryable<TEntity>`, basic collections (`IEnumerable<TEntity>`), or single entities. Complex LINQ involving multiple entity joins, aggregations, or filtering based on business rules must be performed in the Application or Domain Service layers *after* retrieving the necessary base data via simple repository calls.
   - Include comments explaining the business purpose of complex LINQ expressions
   - Implement special solutions for complex SQL patterns like PIVOT operations

3. **Flow Control Implementation**
   - Explicitly implement decision points (DP-XXX) identified in the process analysis
   - Ensure all flow paths (PATH-XXX) are properly represented
   - Map execution outcomes (OC-XXX) to appropriate return structures
   - Implement conditional logic that matches the original procedure's behavior

4. **Returnable Objects Implementation**
   - Create proper C# models for all returnable objects (RO-XXX)
   - Implement conditional return logic matching the original procedure
   - Ensure all execution outcomes return the correct objects under the right conditions
   - Maintain the same data structure and relationship as the original procedure

5. **Side Effects Management**
   - Implement handlers for all identified side effects (SE-XXX)
   - Ensure audit logging and database modifications match the original procedure
   - Maintain proper transaction boundaries for side effects
   - Implement error handling that preserves side effect behavior

6. **Testability**
   - Design all components with unit testing as a primary concern
   - Create interfaces for all dependencies to enable mocking
   - Ensure all classes that need to be mocked have corresponding interfaces
   - Make mapper components implement interfaces rather than relying on concrete implementations
   - Make non-interface methods that need to be mocked virtual
   - Design specific approaches for testing LINQ queries
   - Define clear test seams in every component
   - Avoid static methods and tightly coupled dependencies
   - Design repositories and mappers to be easily substituted with test doubles
   - Create specific testing strategies for conditional flows and returnable objects
   
7. **Data Transformation Strategy**
   - Simple transformations: May be performed in repositories if they're simple column selections
   - Complex transformations (like pivoting): Should be performed in dedicated mapper components
   - Data projections to DTOs: Should be performed in mappers
   - Implement LINQ alternatives for SQL PIVOT operations and other complex patterns

8. **Business Rule Preservation**
   - Map each business rule to specific components and methods
   - Ensure business rules are explicitly enforced by appropriate components
   - Maintain transaction boundaries identified in the process flow
   - Preserve side effect behavior related to business rules

9. **Traceability**
   - Maintain clear links between original SQL and new implementation
   - Document SQL equivalents for repository methods
   - Document transformation equivalents for mapper methods
   - Map business functions to specific implementation components
   - Map returnable objects and side effects to implementation components

10. **Error Handling**
    - Implement exception handling that respects original error paths
    - Provide meaningful error messages and logging
    - Ensure proper transaction rollback on errors
    - Preserve side effect behavior on error conditions

## Data Access Strategy

1. **Entity Framework Core with LINQ**
   - Use EF Core as the primary ORM
   - Define entity models that map to database tables
   - Use LINQ for all query operations
   - Keep repository methods focused on retrieval of raw data. **This means avoiding complex joins, aggregations, or business rule filtering within the repository itself; such logic belongs in higher layers.**
   - Use mapper components for any complex data transformations

2. **LINQ Optimization Strategies**
   - Use appropriate LINQ methods for performance (Where, Select, etc.)
   - Apply proper eager/lazy loading strategies
   - Consider performance implications of complex LINQ translations
   - Document any performance considerations for complex queries
   - Perform complex transformations on materialized collections when appropriate

3. **Complex SQL Pattern Implementation**
   - Develop specific LINQ solutions for PIVOT operations (typically within Mappers or Services)
   - Implement appropriate alternatives for dynamic SQL (likely involving service layer logic)
   - **Plan how complex SQL query patterns (joins, aggregations) will be reconstructed using LINQ in the appropriate service layers (Application/Domain), utilizing data retrieved via simple repository methods.**
   - Ensure performance is maintained for complex transformations (often done post-retrieval in services/mappers)

4. **Transaction Management**
   - Use EF Core transaction support
   - Preserve transaction boundaries from the original procedure
   - Handle transaction lifetime in the appropriate layer
   - Ensure proper rollback on exceptions
   - Maintain side effect behavior within transaction boundaries

## Returnable Objects Strategy

1. **Model Creation**
   - Create C# models for all returnable objects (RO-XXX)
   - Ensure models match the structure of the original SQL result sets
   - Implement proper validation and constraints

2. **Conditional Return Logic**
   - Implement conditional logic that determines which objects are returned
   - Map decision points and flow paths to return conditions
   - Ensure all execution outcomes return the correct objects

3. **Return Type Design**
   - Design return types that accurately represent the original procedure's return behavior
   - Use appropriate types (collections, single objects, primitives) based on the original procedure
   - Include metadata when appropriate

## Migration Strategy Context

This implementation is part of a phased migration strategy:
1. Current phase focuses on preserving 100% functional **outcome** parity, **achieved by correctly implementing the original logic across the appropriate C# layers (Services, Mappers, etc.) using data retrieved via Repositories.**
2. The goal is to standardize APIs while enabling gradual technology evolution
3. Implementation should anticipate future integration with a separate testing stream

Create an implementation plan that provides a comprehensive blueprint for converting the stored procedure to a maintainable, testable C# implementation using the repository pattern with LINQ, while preserving all business functionality, returnable objects, side effects, and execution flow paths.

**CRITICAL:**
- Implementation approach JSON needs to include all repository layer components that are used into the service layer. 
"""

    task = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
{prompt}

ONLY RESPOND JSON AND VALID JSON FOLLOWING THIS TEMPLATE:
{implementation_approach_template}
{specific_considerations_template}
{out_of_scope_template}
"""
            )
        ],
    )
    return task
