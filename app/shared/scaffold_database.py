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

    # Start the scaffolding process
    print(f"Starting database scaffolding for {project_dir}...")

    # Save current directory to restore later
    original_dir = os.getcwd()
    print(f"Current directory before: {original_dir}")
    print(f"Project directory exists: {os.path.exists(project_dir)}")
    print(
        f"Program.cs exists: {os.path.exists(os.path.join(project_dir, 'Program.cs'))}"
    )

    try:
        # Change to the project directory for the dotnet ef command
        os.chdir(project_dir)
        print(f"Current directory after: {os.getcwd()}")
        print(f"Program.cs exists in current directory: {os.path.exists('Program.cs')}")
        print(f"Files in current directory: {os.listdir('.')}")

        # Option 2: Use the dotnet ef command directly
        # This approach is simpler and more reliable
        print("Using dotnet ef command for scaffolding...")
        scaffold_command = 'dotnet ef dbcontext scaffold "Name=DefaultConnection" Microsoft.EntityFrameworkCore.SqlServer -o Models --data-annotations -c AppDbContext --context-dir Data --context-namespace sql2code.Data --namespace sql2code.Models'
        print(f"Executing: {scaffold_command}")

        # Execute the command
        result = subprocess.run(
            scaffold_command, shell=True, capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"Error executing scaffolding command: {result.stderr}")
            return False

        # Print the output
        print("Scaffolding completed successfully!")
        if result.stdout:
            print(result.stdout)

        # Update Program.cs to include DbContext configuration
        update_program_cs(project_dir, context_namespace, context_name)

        # Update model files with namespace imports
        update_model_files("./Models", model_namespace)

        # Update DbContext with explicit model namespace paths
        update_dbcontext_paths("./Data/AppDbContext.cs", model_namespace)

        # Add abstractions to the project
        print("\nAdding abstractions to the project...")
        try:
            add_abstractions(project_name)
        except Exception as e:
            print(f"Error during scaffolding: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

        # Generate repositories
        print("\nGenerating repositories for each model...")
        try:
            generate_repositories(project_name)
        except Exception as e:
            print(f"Error generating repositories: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

        return True

    except Exception as e:
        print(f"Error during scaffolding: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Restore original directory
        os.chdir(original_dir)
