#!/usr/bin/env python3
"""
Script to generate repository classes for each model in the project.
This script creates the following for each model:
1. Interface for the repository (I{ModelName}Repository.cs)
2. Implementation of the repository ({ModelName}Repository.cs)

Usage:
    python generate_repository.py
"""

import os

# Configuration - use relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(os.path.dirname(SCRIPT_DIR), "output", "csharp-code")
MODELS_DIR = os.path.join(PROJECT_ROOT, "Models")
REPOSITORIES_DIR = os.path.join(PROJECT_ROOT, "Repositories")


def get_model_names():
    """Extract model names from C# files in the Models directory"""
    model_names = []
    for file in os.listdir(MODELS_DIR):
        if file.endswith(".cs") and not file.startswith("."):
            model_name = file[:-3]  # Remove .cs extension
            model_names.append(model_name)
    return sorted(model_names)


def create_directory_for_model(model_name):
    """Create a directory for the model's repository if it doesn't exist"""
    model_repo_dir = os.path.join(REPOSITORIES_DIR, model_name)
    os.makedirs(model_repo_dir, exist_ok=True)
    return model_repo_dir


def generate_repository_interface(model_name, model_repo_dir):
    """Generate the repository interface for a model"""
    interface_content = f"""using sql2code.Abstractions.Repositories;
using sql2code.Models;

namespace sql2code.Repositories.{model_name}
{{
    /// <summary>
    /// Repository interface for {model_name} operations
    /// </summary>
    public interface I{model_name}Repository : IRepository<sql2code.Models.{model_name}>
    {{
        // Add specific methods for {model_name} if needed
    }}
}}
"""
    interface_path = os.path.join(model_repo_dir, f"I{model_name}Repository.cs")
    with open(interface_path, "w") as f:
        f.write(interface_content)
    return interface_path


def generate_repository_implementation(model_name, model_repo_dir, is_keyless=False):
    """Generate the repository implementation for a model"""
    # Add special handling for keyless entities
    keyless_comment = ""
    base_class = "Repository<sql2code.Models.{model_name}>"

    if is_keyless:
        keyless_comment = """
        // This is a keyless entity, so some operations that require a primary key may not work
        // Method overrides have been implemented to handle the keyless nature of this entity
        """
        base_class = "KeylessRepository<sql2code.Models.{model_name}>"

    implementation_content = f"""using sql2code.Abstractions.Repositories;
using sql2code.Data;
using sql2code.Models;

namespace sql2code.Repositories.{model_name}
{{
    /// <summary>
    /// Repository implementation for {model_name} operations
    /// </summary>
    public class {model_name}Repository : {base_class.format(model_name=model_name)}, I{model_name}Repository
    {{
        // No need to redefine _context as it's already available from base class (ReadRepository){keyless_comment}
        
        /// <summary>
        /// Initializes a new instance of the {model_name}Repository class
        /// </summary>
        /// <param name="context">Database context</param>
        public {model_name}Repository(AppDbContext context) : base(context)
        {{
            // Base constructor handles context initialization
        }}
        
        // Add specific implementation methods for {model_name} if needed
    }}
}}
"""
    implementation_path = os.path.join(model_repo_dir, f"{model_name}Repository.cs")
    with open(implementation_path, "w") as f:
        f.write(implementation_content)
    return implementation_path


def is_keyless_entity(model_name):
    """Determine if a model is a keyless entity by checking for the [Keyless] attribute"""
    model_file_path = os.path.join(MODELS_DIR, f"{model_name}.cs")

    if not os.path.exists(model_file_path):
        print(f"Warning: Model file {model_file_path} not found")
        return False

    try:
        with open(model_file_path, "r") as file:
            content = file.read()
            # Check if the [Keyless] attribute is present
            if "[Keyless]" in content:
                return True
            return False
    except Exception as e:
        print(f"Error reading model file {model_file_path}: {str(e)}")
        return False


def generate_repositories(project_name):
    """Main function to generate repositories files"""
    # Verify that the Models directory exists
    if not os.path.exists(MODELS_DIR):
        print(f"Error: Models directory not found at {MODELS_DIR}")
        print("Please make sure the path is correct and the project is generated.")
        return False

    # Create the Repositories directory if it doesn't exist
    os.makedirs(REPOSITORIES_DIR, exist_ok=True)

    # Get all model names
    model_names = get_model_names()
    print(f"Found {len(model_names)} models")

    try:
        # Generate repositories for each model
        for model_name in model_names:
            print(f"Processing model: {model_name}")

            # Create directory for the model
            model_repo_dir = create_directory_for_model(model_name)

            # Check if this is a keyless entity
            keyless = is_keyless_entity(model_name)
            if keyless:
                print(f"  {model_name} is a keyless entity")

            # Generate repository interface
            interface_path = generate_repository_interface(model_name, model_repo_dir)
            print(f"  Created interface: {interface_path}")

            # Generate repository implementation
            implementation_path = generate_repository_implementation(
                model_name, model_repo_dir, is_keyless=keyless
            )
            print(f"  Created implementation: {implementation_path}")

        print("Done!")
        return True

    except Exception as e:
        print(f"Error generating repositories: {str(e)}")
        return False
