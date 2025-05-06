import os
import shutil
import sys
from pathlib import Path


def copy_template(project_name):
    """
    Copy the C# template project from the template-code directory to the output/csharp-code directory.
    Uses relative paths to ensure portability.
    """
    # Get the script directory
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # Calculate the path to the template-code directory (going up from 'shared' folder)
    template_dir = os.path.join("app", "shared", "scaffold_templates", "template-code")

    # Create output directory path
    output_dir = os.path.join("app", "output", project_name, "csharp-code")

    # Check if the template directory exists
    if not os.path.exists(template_dir):
        print(f"Error: Template directory not found at: {template_dir}")
        sys.exit(1)

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_dir), exist_ok=True)  # Create output directory

    print(f"Copying C# template from: {template_dir}")
    print(f"To: {output_dir}")

    try:
        # Remove existing output directory if it exists
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

        # Copy all content from template directory to destination
        shutil.copytree(template_dir, output_dir)

        print("C# template copied successfully!")
        return True

    except Exception as e:
        print(f"Error copying template: {e}")
        sys.exit(1)
