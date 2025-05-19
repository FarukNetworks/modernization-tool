from google.genai import types
import json
import os
import re


important_rules = """
<important_rules>
<rule>
ONLY CREATE 1 TEST THAT IS SPECIFIED IN THE TEST SCENARIO.
</rule>
<rule>
ALL THE TESTS NEEDS TO BE SUCCESSFUL.
</rule>
<rule>
**CRITICAL MOCKABILITY RULES:**
1. With Moq, you can ONLY mock:
   - Interfaces
   - Virtual methods in classes
   - Abstract methods in classes
2. DO NOT attempt to mock non-virtual methods in concrete classes
3. Always prefer mocking interfaces over concrete classes
4. If you see `_mock<ConcreteClass>`, change it to `_mock<IInterfaceName>` 
5. Check that all methods being mocked through `Setup()` are either:
   - Methods from an interface
   - Virtual methods from a base class
6. Replace any non-mockable method setups with appropriate alternatives
</rule>
</important_rules>
"""


def get_prompt(procedure_name, project_path, scenario):
    """
    Generate prompt for test generation

    Args:
        procedure_name: Name of the procedure
        procedure_definition: SQL code of the procedure
        project_path: Project path

    Returns:
        Prompt for the agent
    """

    # Get scenario ID from either 'id' or 'testId' field
    scenario_id = scenario.get("testId", scenario.get("id", "unknown"))

    # If the scenario ID is part of a test name like "BR-001-positive", extract it
    if "-" in scenario_id:
        # Extract just the ID part (e.g., "BR-001" from "BR-001-positive")
        scenario_id = scenario_id.split("-")[0] + "-" + scenario_id.split("-")[1]

    procedure_name_only = procedure_name.split(".")[-1]

    # EF analysis
    with open(
        f"{project_path}/analysis/{procedure_name}/{procedure_name}_ef_analysis.json",
        "r",
    ) as f:
        ef_analysis = json.load(f)

    # Get all service files
    service_files = []
    service_dir = f"{project_path}/csharp-code/Services/{procedure_name_only}_Services"
    if os.path.exists(service_dir):
        for file in os.listdir(service_dir):
            if file.endswith(".cs"):
                service_files.append(os.path.join(service_dir, file))

    procedure_services = []
    service_name = None  # Initialize service_name
    service_interface_name = None  # Initialize service_interface_name

    # Read each service file
    for service_file in service_files:
        # Get service file name
        service_file_name = os.path.basename(service_file)
        procedure_name_with_service = procedure_name_only + "_Service.cs"
        procedure_name_with_service_interface = (
            "I" + procedure_name_only + "_Service.cs"
        )
        if service_file_name == procedure_name_with_service:
            service_name = service_file_name
            with open(service_file, "r") as f:
                service_content = f.read()
            procedure_services.append(service_file)
            print(f"✅ Found service file: {service_name}")

        if service_file_name == procedure_name_with_service_interface:
            service_interface_name = service_file_name
            procedure_services.append(service_file)
            print(f"✅ Found service interface file: {service_interface_name}")

    if not service_name:
        raise ValueError(
            f"No service file found for procedure {procedure_name}. Expected file: {procedure_name}_Service.cs"
        )

    service_name_base = service_name.replace(".cs", "")
    procedure_services_content = []
    for procedure_service in procedure_services:
        with open(procedure_service, "r") as f:
            procedure_services_content.append(f.read())

    # Get namespace and method from the service content
    service_namespace = re.search(
        r"namespace\s+sql2code\.Services\.\w+", service_content
    )
    if service_namespace:
        service_namespace = service_namespace.group(0)
    else:
        service_namespace = "namespace sql2code.Services"

    # Read the ef_analysis and get all model paths
    model_names = []
    model_file_paths = []
    repositories = []
    for model in ef_analysis["entity_framework_analysis"]["related_models"]:
        model_names.append(model["db_set_name"])
        model_file_paths.append(model["model_file_path"])

    # Read each model file and store the content
    model_files_content = []
    for model_file_path in model_file_paths:
        with open(f"{project_path}/csharp-code/{model_file_path}", "r") as f:
            model_files_content.append(f.read())

    # Read the DbContext file and extract only relevant model configurations
    relevant_dbcontext_content = ""
    dbcontext_path = f"{project_path}/csharp-code/Data/AppDbContext.cs"
    if os.path.exists(dbcontext_path):
        with open(dbcontext_path, "r") as f:
            full_dbcontext = f.read()

        # Create a set of model names (both plural and singular forms)
        model_set = set()
        for model_name in model_names:
            model_set.add(model_name)
            # Add singular form (removing 's' if it exists)
            singular_name = model_name.rstrip("s")
            model_set.add(singular_name)

        # Extract relevant DbSet properties
        dbset_sections = []
        for model_name in model_names:
            pattern = rf"public\s+virtual\s+DbSet<[^>]*>\s+{model_name}\s+\{{[^}}]*}}"
            match = re.search(pattern, full_dbcontext)
            if match:
                dbset_sections.append(match.group(0))

        # Extract model configurations from OnModelCreating
        model_config_sections = {}

        # Get all entity configurations
        for singular_name in {name.rstrip("s") for name in model_names}:
            pattern = rf"modelBuilder\.Entity<[^>]*{singular_name}[^>]*>\(entity\s*=>\s*\{{(?:[^{{}}]|(?:\{{[^{{}}]*}}))*?}}\);"
            matches = re.finditer(pattern, full_dbcontext, re.DOTALL)
            for match in matches:
                # Use the match text as key to avoid duplicates
                model_config_sections[match.group(0)] = match.group(0)

        # Find any related entities mentioned in the configurations
        # This extracts relationships from already found configurations
        related_entities = set()
        for config in model_config_sections.values():
            # Find entity.HasOne(d => d.RelatedEntity) patterns
            relations = re.findall(r"entity\.HasOne\(d\s*=>\s*d\.(\w+)\)", config)
            for relation in relations:
                related_entities.add(relation)

            # Find entity.WithMany(p => p.RelatedEntities) patterns
            collections = re.findall(r"WithMany\(p\s*=>\s*p\.(\w+)\)", config)
            for collection in collections:
                # Add singular form for potential lookup
                related_entities.add(collection.rstrip("s"))

        # Look for configurations of related entities not already captured
        for related_entity in related_entities:
            if related_entity not in {name.rstrip("s") for name in model_names}:
                # Try to find its DbSet
                dbset_pattern = rf"public\s+virtual\s+DbSet<[^>]*>\s+{related_entity}s\s+\{{[^}}]*}}"
                dbset_match = re.search(dbset_pattern, full_dbcontext)
                if dbset_match and dbset_match.group(0) not in dbset_sections:
                    dbset_sections.append(dbset_match.group(0))

                # Try to find its configuration
                config_pattern = rf"modelBuilder\.Entity<[^>]*{related_entity}[^>]*>\(entity\s*=>\s*\{{(?:[^{{}}]|(?:\{{[^{{}}]*}}))*?}}\);"
                config_matches = re.finditer(config_pattern, full_dbcontext, re.DOTALL)
                for match in config_matches:
                    model_config_sections[match.group(0)] = match.group(0)

        # Build relevant content with imports
        relevant_dbcontext_content = (
            "// Relevant parts of DbContext extracted for testing\n"
        )
        relevant_dbcontext_content += "using System;\nusing Microsoft.EntityFrameworkCore;\nusing sql2code.Models;\n\nnamespace sql2code.Data;\n\n"
        relevant_dbcontext_content += (
            "public partial class AppDbContext : DbContext\n{\n"
        )
        relevant_dbcontext_content += "    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) {}\n\n"

        # Add relevant DbSet properties
        for section in dbset_sections:
            relevant_dbcontext_content += f"    {section}\n\n"

        # Add OnModelCreating method with relevant configurations
        if model_config_sections:
            relevant_dbcontext_content += "    protected override void OnModelCreating(ModelBuilder modelBuilder)\n    {\n"
            for section in model_config_sections.values():
                relevant_dbcontext_content += f"        {section}\n\n"
            relevant_dbcontext_content += "    }\n"

        relevant_dbcontext_content += "}"

    # Read the main service file
    with open(
        f"{project_path}/csharp-code/Services/{procedure_name_only}_Services/{service_name}",
        "r",
    ) as f:
        service_content = f.read()

    # Get all using statements from the service content
    using_statements = []
    for line in service_content.split("\n"):
        if line.startswith("using"):
            using_statements.append(line)

    # Get and read any DTO files
    dto_files = []
    dto_dirs = [
        f"{project_path}/csharp-code/DTOs/{procedure_name_only}",
    ]
    for dto_dir in dto_dirs:
        if os.path.exists(dto_dir):
            for file in os.listdir(dto_dir):
                if file.endswith(f".cs"):
                    dto_files.append(os.path.join(dto_dir, file))

    dto_files_content = []
    for dto_file in dto_files:
        with open(dto_file, "r") as f:
            dto_files_content.append(f.read())

    mapper_dir = f"{project_path}/csharp-code/Mappers/{procedure_name_only}"
    mapper_files = []
    if os.path.exists(mapper_dir):
        for file in os.listdir(mapper_dir):
            if file.endswith(f".cs"):
                mapper_files.append(os.path.join(mapper_dir, file))

    mapper_files_content = []
    for mapper_file in mapper_files:
        with open(mapper_file, "r") as f:
            mapper_files_content.append(f.read())

    csharp_template = f"""
using System;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;
using sql2code.Data;
using sql2code.Models;
using sql2code.DTOs.{procedure_name_only}; // adjust if DTO namespace differs

namespace sql2code.Tests.{procedure_name_only}_{scenario_id}
{{
    public class {procedure_name_only}_{scenario_id}_Tests
        : IClassFixture<WebApplicationFactory<Program>>
    {{
        private readonly WebApplicationFactory<Program> _factory;
        private readonly HttpClient _client;

        public {procedure_name_only}_{scenario_id}_Tests(WebApplicationFactory<Program> factory)
        {{
            _factory = factory
                .WithWebHostBuilder(builder =>
                {{
                    builder.ConfigureServices(services =>
                    {{
                        // Replace production DbContext with In-Memory provider
                        var descriptor = services.Single(
                            d => d.ServiceType == typeof(DbContextOptions<AppDbContext>));
                        services.Remove(descriptor);

                        services.AddDbContext<AppDbContext>(options =>
                            options.UseInMemoryDatabase("{{procedure_name_only}}_{{scenario_id}}"));
                    }});
                }});

            _client = _factory.CreateClient();

            // Seed scenario data
            using var scope = _factory.Services.CreateScope();
            var ctx = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            SeedScenarioData(ctx);
        }}

        private static void SeedScenarioData(AppDbContext ctx)
        {{
            // === Begin SCENARIO testDataSetup ===
            {scenario["testDataSetup"]}
            

            // Extract the testDataSetup and and it to the inMemoryDatabase
            // EXAMPLE: 
            var customer = new Customer
            {{
                CustomerId = 1,
                FirstName  = "John",
                LastName   = "Doe",
                Email      = "john.doe@example.com",
                DateRegistered = DateTime.UtcNow
            }};
            ctx.Customers.Add(customer);


            ctx.SaveChanges();
            // === End SCENARIO testDataSetup ===
        }}

        [Fact]
        public async Task {procedure_name_only}_{scenario_id}_validation()
        {{
            {scenario["validationCriteria"]}
            // Act – hit the real API endpoint (adjust path/query as in controller)
            var dto = await _client.GetFromJsonAsync<dtoName[]>(
                $"/api/apiEndPoint?testParameters=testParameterValue");

            // Assert – validationCriteria expectedResult
            Assert.NotNull(dto);
            var actualResult = Assert.Single(dto);

            Assert.Equal(1, actualResult.CustomerID);
        }}
    }}
}}
"""

    # Format the prompt
    prompt = f"""
Generate a concise xUnit integration test for using EF Core's InMemoryDatabase.

### Instructions

* Populate the `SeedScenarioData()` method explicitly from the provided JSON scenario (`testDataSetup`). Ensure data types and relationships exactly match as defined.
* Execute the service method `SERVICE_METHOD_NAME` using parameters explicitly from the provided `testParameters`.
* Assert the results strictly based on the provided `validationCriteria.expectedResult`.

### Provided Files

* **Scenario Data:**

```json
{scenario}
```

* **Service Implementation:**

```csharp
{service_content}
```

* **Minimal DbContext Definition (use only this definition):**

```csharp
{relevant_dbcontext_content}
```

* **DTO Definitions:**

```csharp
{dto_files_content}
```

* **Model Definitions:**

```csharp
{model_files_content}
```

### Critical Rules

* **NO MOCKS**: Do NOT use Moq or any mocks for DbContext or repositories. Directly interact with the provided minimal DbContext using EF Core's InMemoryDatabase.
* Ensure the test is immediately compilable and runnable without further modification.
* The assertions must exactly match the fields defined in `validationCriteria.expectedResult`.

**Project packages:**
   Top-level Package                               Requested   Resolved
   > Microsoft.AspNetCore.OpenApi                  7.0.0       7.0.0
   > Microsoft.Data.SqlClient                      6.0.1       6.0.1
   > Microsoft.EntityFrameworkCore                 9.0.3       9.0.3
   > Microsoft.EntityFrameworkCore.Design          9.0.3       9.0.3
   > Microsoft.EntityFrameworkCore.InMemory        9.0.3       9.0.3
   > Microsoft.EntityFrameworkCore.Relational      9.0.3       9.0.3
   > Microsoft.EntityFrameworkCore.SqlServer       9.0.3       9.0.3
   > Microsoft.NET.Test.Sdk                        17.12.0     17.12.0
   > Moq                                           4.20.72     4.20.72
   > Moq.EntityFrameworkCore                       7.0.0.2     7.0.0.2
   > Newtonsoft.Json                               13.0.3      13.0.3
   > Swashbuckle.AspNetCore                        6.5.0       6.5.0
   > xUnit                                         2.9.3       2.9.3
   > xunit.runner.visualstudio                     3.0.2       3.0.2

{important_rules}
"""

    task = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
{prompt}

<output_format>
{csharp_template}
</output_format>
"""
            )
        ],
    )
    return task
