import os
import shutil
from pathlib import Path


def add_abstractions(project_name):
    """
    Copy abstractions from the Abstractions directory to the csharp-code project
    and modify Program.cs to add necessary using statements and service registrations.
    """
    # Get the script directory and calculate paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    abstractions_dir = os.path.join(script_dir, "Abstractions")
    output_dir = os.path.join(root_dir, "app", "output", project_name, "csharp-code")

    print(f"Adding abstractions from: {abstractions_dir}")
    print(f"To project in: {output_dir}")

    try:
        # Copy Abstractions directory
        dest_abstractions = os.path.join(output_dir, "Abstractions")
        if os.path.exists(dest_abstractions):
            shutil.rmtree(dest_abstractions)
        shutil.copytree(abstractions_dir, dest_abstractions)
        print("Abstractions copied successfully!")

        # Modify Program.cs
        program_cs_path = os.path.join(output_dir, "Program.cs")
        if not os.path.exists(program_cs_path):
            print("Error: Program.cs not found!")
            return False

        with open(program_cs_path, "r") as file:
            content = file.read()

        # Add using statements at the top
        using_statements = """using sql2code.Abstractions.Repositories;
using sql2code.Data;

"""
        if "using sql2code.Abstractions.Repositories;" not in content:
            # Find the first using statement
            first_using_index = content.find("using")
            if first_using_index != -1:
                content = (
                    content[:first_using_index]
                    + using_statements
                    + content[first_using_index:]
                )

        # Add service registrations after EF configuration
        service_registrations = """
// Register repository services (includes both generic and specific repositories)
builder.Services.AddRepositoryServices();

"""
        # Find position after complete EF configuration
        ef_config_index = content.find("builder.Services.AddDbContext")
        if ef_config_index != -1:
            # Find the end of the complete EF configuration by looking for the closing parenthesis
            line_end = content.find("));", ef_config_index)
            if line_end != -1:
                # Move past the "));
                line_end += 3
                content = (
                    content[:line_end] + service_registrations + content[line_end:]
                )

        # Write back the modified content
        with open(program_cs_path, "w") as file:
            file.write(content)

        print("Program.cs modified successfully!")
        return True

    except Exception as e:
        print(f"Error adding abstractions: {e}")
        import traceback

        traceback.print_exc()  # Add stack trace for better debugging
        return False
