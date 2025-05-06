import os
import subprocess
import sys
import re

# Add the parent directory to the path so we can import from shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.scaffold_templates.create_csharp_template import copy_template
from shared.scaffold_templates.add_abstractions import add_abstractions
from shared.scaffold_templates.generate_repository import generate_repositories


def update_program_cs(project_dir, context_namespace, context_name):
    """
    Updates Program.cs to include the DbContext configuration after scaffolding.
    """
    # Since we've already changed to the project directory, use local path
    program_cs_path = "Program.cs"

    try:
        print(f"Looking for Program.cs at: {os.path.abspath(program_cs_path)}")

        # Check if file exists
        if not os.path.exists(program_cs_path):
            print(f"Error: Program.cs not found at {os.path.abspath(program_cs_path)}")
            # List files in current directory to debug
            print("Files in current directory:", os.listdir("."))
            return False

        # Read the current Program.cs content
        with open(program_cs_path, "r") as f:
            content = f.read()

        # Find the position to insert the DbContext configuration
        insert_pos = content.find("builder.Services.AddSwaggerGen();")
        if insert_pos == -1:
            print("Warning: Could not find insertion point in Program.cs")
            return False

        # Find the end of the line
        insert_pos = content.find("\n", insert_pos) + 1

        # Define the DbContext configuration
        db_context_config = f"""
// Configure Entity Framework
builder.Services.AddDbContext<{context_namespace}.{context_name}>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));
"""

        # Insert the DbContext configuration
        new_content = content[:insert_pos] + db_context_config + content[insert_pos:]

        # Write the updated content back to Program.cs
        with open(program_cs_path, "w") as f:
            f.write(new_content)

        print("✅ Updated Program.cs with DbContext configuration")
        return True

    except Exception as e:
        print(f"Error updating Program.cs: {str(e)}")
        print(f"Current directory: {os.getcwd()}")
        return False


def update_model_files(model_dir, model_namespace):
    """
    Adds the using statement for the model namespace to each model file to avoid ambiguous reference.
    This ensures all models can reference each other without fully qualified names.
    """
    print(f"Updating model files in {model_dir} to include namespace import...")

    if not os.path.exists(model_dir):
        print(f"Error: Model directory {model_dir} does not exist.")
        return False

    # Count of files updated
    updated_count = 0

    # Loop through all .cs files in the model directory
    for filename in os.listdir(model_dir):
        if filename.endswith(".cs"):
            file_path = os.path.join(model_dir, filename)

            # Read the file content
            with open(file_path, "r") as f:
                content = f.read()

            # Check if the using statement is already present
            if f"using {model_namespace};" not in content:
                # Simply add the namespace import at the beginning of the file
                new_content = f"using {model_namespace};\n\n" + content

                # Write the updated content back
                with open(file_path, "w") as f:
                    f.write(new_content)

                updated_count += 1
                print(f"Updated {filename} with '{model_namespace}' import")

    print(f"✅ Updated {updated_count} model files with '{model_namespace}' import")
    return True


def update_dbcontext_paths(dbcontext_path, model_namespace):
    """
    Updates AppDbContext.cs to add explicit namespace paths to all entity references.
    Adds full namespace path to DbSet properties and Entity configurations.
    """
    print(
        f"Updating DbContext at {dbcontext_path} with explicit model namespace paths..."
    )

    if not os.path.exists(dbcontext_path):
        print(f"Error: DbContext file {dbcontext_path} does not exist.")
        return False

    # Read the file content
    with open(dbcontext_path, "r") as f:
        content = f.read()

    # Update DbSet declarations
    # From: public virtual DbSet<LogLevel> LogLevels { get; set; }
    # To:   public virtual DbSet<csharp-code.Models.LogLevel> LogLevels { get; set; }
    updated_content = re.sub(
        r"public\s+virtual\s+DbSet<([^.<>]+)>\s+([^{]+){",
        f"public virtual DbSet<{model_namespace}.\\1> \\2{{",
        content,
    )

    # Update Entity configurations
    # From: modelBuilder.Entity<Action>(entity =>
    # To:   modelBuilder.Entity<csharp-code.Models.Action>(entity =>
    updated_content = re.sub(
        r"modelBuilder\.Entity<([^.<>]+)>\((entity|e)\s*=>",
        f"modelBuilder.Entity<{model_namespace}.\\1>(\\2 =>",
        updated_content,
    )

    # Write the updated content back
    with open(dbcontext_path, "w") as f:
        f.write(updated_content)

    print(f"✅ Updated AppDbContext.cs with explicit model namespace paths")
    return True


def scaffold_database(folder_path, project_name):
    """
    Python script that replaces the dotnet ef dbcontext scaffold command.
    Creates necessary files for database scaffolding in the C# project.
    """
    # First, create the C# template project
    if not copy_template(project_name):
        print("Failed to create C# template project")
        return False

    # Paths
    project_dir = f"app/output/{project_name}/{folder_path}"
    model_dir = os.path.join(project_dir, "Models")
    data_dir = os.path.join(project_dir, "Data")

    # Connection info
    connection_string = os.getenv("CONNECTION_STRING_CSHARP")
    context_name = "AppDbContext"
    context_namespace = "sql2code.Data"
    model_namespace = "sql2code.Models"
    schema = "dbo"

    # Ensure the project directory exists
    if not os.path.exists(project_dir):
        print(f"Error: Project directory {project_dir} does not exist.")
        print("Run create_csharp_template.py first to create the project.")
        return False

    # Create Model and Data directories if they don't exist
    for directory in [model_dir, data_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

    # There are two approaches:
    # 1. Use a temporary C# file to do the scaffolding
    # 2. Use the dotnet ef command directly

    # Option 1: Create and execute a C# file
    # This approach is more flexible and easier to customize
    scaffold_code = f"""using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.EntityFrameworkCore.Scaffolding;
using Microsoft.Extensions.DependencyInjection;

namespace DatabaseScaffolder
{{
    public class Program
    {{
        public static void Main(string[] args)
        {{
            Console.WriteLine("Starting database scaffolding...");
            
            // Connection string and configuration
            string connectionString = "{connection_string}";
            string provider = "Microsoft.EntityFrameworkCore.SqlServer";
            string outputDir = Path.Combine(Directory.GetCurrentDirectory(), "Model");
            string contextDir = Path.Combine(Directory.GetCurrentDirectory(), "Data");
            string contextName = "{context_name}";
            string schema = "{schema}";
            
            // Create directories if they don't exist
            Directory.CreateDirectory(outputDir);
            Directory.CreateDirectory(contextDir);
            
            // Set up services for scaffolding
            var serviceProvider = new ServiceCollection()
                .AddEntityFrameworkDesignTime()
                .BuildServiceProvider();
            
            var scaffolder = serviceProvider.GetRequiredService<IReverseEngineerScaffolder>();
            
            // Configure scaffolding options
            var options = new ReverseEngineerOptions
            {{
                ConnectionString = connectionString,
                ContextName = contextName,
                OutputPath = Directory.GetCurrentDirectory(),
                ProjectPath = Directory.GetCurrentDirectory(),
                ContextNamespace = "{context_namespace}",
                ModelNamespace = "{context_namespace.replace('.Data', '.Model')}",
                ContextDir = "Data",
                UseDataAnnotations = true
            }};
            
            // Define tables to include (from the specified schema)
            var tableSelectionSet = new TableSelectionSet
            {{
                Schemas = new List<string> {{ schema }}
            }};
            
            try
            {{
                // Perform the scaffolding
                var result = scaffolder.ScaffoldModel(
                    connectionString,
                    tableSelectionSet,
                    options
                );
                
                Console.WriteLine($"Successfully scaffolded database to {{outputDir}} with context in {{contextDir}}");
            }}
            catch (Exception ex)
            {{
                Console.WriteLine($"Error during scaffolding: {{ex.Message}}");
                Console.WriteLine(ex.StackTrace);
            }}
        }}
    }}
}}
"""

    # Option 2: Direct dotnet ef command
    # This is simpler but less flexible
    dotnet_ef_command = f'dotnet ef dbcontext scaffold "Name=DefaultConnection" Microsoft.EntityFrameworkCore.SqlServer -o Models --data-annotations -c {context_name} --context-dir Data --context-namespace {context_namespace} --namespace {context_namespace.replace(".Data", ".Models")}'

    # Choose which approach to use
    use_dotnet_ef = True  # Set to False to use the C# file approach

    print(f"Starting database scaffolding for {project_dir}...")

    try:
        # Print current directory and verify project dir exists
        print(f"Current directory before: {os.getcwd()}")
        print(f"Project directory exists: {os.path.exists(project_dir)}")
        print(
            f"Program.cs exists: {os.path.exists(os.path.join(project_dir, 'Program.cs'))}"
        )

        # Change directory to the project
        current_dir = os.getcwd()
        os.chdir(project_dir)

        print(f"Current directory after: {os.getcwd()}")
        print(f"Program.cs exists in current directory: {os.path.exists('Program.cs')}")
        print(f"Files in current directory: {os.listdir('.')}")

        if use_dotnet_ef:
            # Approach 2: Use dotnet ef command directly
            print("Using dotnet ef command for scaffolding...")
            print(f"Executing: {dotnet_ef_command}")

            process = subprocess.run(
                dotnet_ef_command, shell=True, text=True, capture_output=True
            )

            if process.returncode == 0:
                print("Scaffolding completed successfully!")
                print(process.stdout)
            else:
                print(f"Error executing scaffolding command: {process.stderr}")
                print("\nTrying alternative approach...")
                use_dotnet_ef = False  # Fall back to C# file approach

        if not use_dotnet_ef:
            # Approach 1: Create and run C# file
            print("Using C# file for scaffolding...")

            if process.returncode == 0:
                print("Scaffolding completed successfully!")
                print(process.stdout)
            else:
                print(f"Error during scaffolding: {process.stderr}")
                os.chdir(current_dir)  # Make sure we return to original directory
                return False

        # Update Program.cs to include the DbContext configuration
        update_result = update_program_cs(project_dir, context_namespace, context_name)
        if not update_result:
            print("Failed to update Program.cs")

        # Update model files to include the model namespace
        update_model_files(os.path.join(".", "Models"), model_namespace)

        # Update AppDbContext.cs to use explicit namespace paths
        dbcontext_path = os.path.join(".", "Data", "AppDbContext.cs")
        update_dbcontext_paths(dbcontext_path, model_namespace)

        # Return to original directory
        os.chdir(current_dir)

        # Add abstractions after scaffolding is complete
        print("\nAdding abstractions to the project...")
        if not add_abstractions(project_name):
            print("Failed to add abstractions")
            return False
        print("✅ Abstractions added successfully!")

        # Generate repositories and unit of work for each model
        print("\nGenerating repositories and unit of work...")
        if not generate_repositories(project_name):
            print("Failed to generate repositories")
            return False
        print("✅ Repositories and unit of work generated successfully!")

        return True

    except Exception as e:
        print(f"Error during scaffolding: {str(e)}")
        # Ensure we return to the original directory
        if os.getcwd() != current_dir:
            os.chdir(current_dir)
        return False
