#!/usr/bin/env python3

import os
import json
import re
from pathlib import Path


class EntityFrameworkAnalyzer:
    def __init__(self, procedure_name, project_path):
        self.procedure_name = procedure_name
        self.project_path = Path(project_path)
        self.output_dir = self.project_path / "analysis" / procedure_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csharp_code_dir = self.project_path / "csharp-code"
        self.sql_raw_dir = self.project_path / "sql_raw" / procedure_name

        # Store the tables to analyze
        self.tables = []

        # Store the collected data
        self.collected_data = {
            "entity_framework_analysis": {
                "related_models": [],
                "base_repository_path": "",
            }
        }

    def extract_tables_from_sql(self):
        """Extract table names from the SQL file"""
        sql_file = self.sql_raw_dir / f"{self.procedure_name}.sql"

        if not sql_file.exists():
            print(f"SQL file not found: {sql_file}")
            return []

        sql_content = sql_file.read_text()

        # Extract table names using multiple patterns to catch more references
        table_patterns = [
            # Standard FROM/JOIN/UPDATE/INTO pattern
            r"(?:FROM|JOIN|UPDATE|INTO)\s+(\[?[a-zA-Z0-9_\.]+\]?)",
            # Tables in INSERT statements
            r"INSERT\s+INTO\s+(\[?[a-zA-Z0-9_\.]+\]?)",
            # Tables in DELETE statements
            r"DELETE\s+FROM\s+(\[?[a-zA-Z0-9_\.]+\]?)",
            # Explicit table references in column selections
            r"(\[?[a-zA-Z0-9_\.]+\]?)\.\[?[a-zA-Z0-9_]+\]?",
        ]

        tables = set()

        for pattern in table_patterns:
            for match in re.finditer(pattern, sql_content, re.IGNORECASE):
                table_name = match.group(1).strip("[]").strip()
                # Skip common SQL keywords that might be captured
                if table_name.lower() not in [
                    "from",
                    "where",
                    "select",
                    "group",
                    "order",
                    "having",
                ]:
                    # Skip numeric values that appear to be numbers, not table names
                    if not re.match(r"^\d+$", table_name):
                        # Skip short abbreviations that might be aliases (2-3 characters)
                        if len(table_name) > 3 or "." in table_name:
                            tables.add(table_name)

        # Clean up table names (remove schema prefixes for comparison)
        clean_tables = []
        for table in tables:
            # Store the original table name with schema if present
            if "." in table:
                schema, table_name = table.split(".", 1)
                clean_tables.append(
                    {"full_name": table, "schema": schema, "name": table_name}
                )
            else:
                clean_tables.append({"full_name": table, "schema": None, "name": table})

        print(
            f"Extracted {len(clean_tables)} tables from SQL file: {', '.join([t['full_name'] for t in clean_tables])}"
        )
        return clean_tables

    def set_tables(self, tables):
        """Set the tables to analyze"""
        self.tables = tables

    def analyze(self):
        """Run the entity framework analysis"""
        # Check if analysis file already exists
        output_file = self.output_dir / f"{self.procedure_name}_ef_analysis.json"
        if output_file.exists():
            print(
                f"Analysis file already exists for {self.procedure_name}, skipping..."
            )
            return None

        # Extract tables from SQL file if none provided
        if not self.tables:
            self.tables = self.extract_tables_from_sql()

        if not self.tables:
            print(
                f"No tables found for procedure {self.procedure_name}. Skipping analysis."
            )
            return None

        self.find_related_entities()
        self.analyze_repository_files()
        self.save_report()
        return self.collected_data["entity_framework_analysis"]

    def find_related_entities(self):
        """Find related entity models and DbContext configurations"""
        print("Finding related entities...")
        models_dir = self.csharp_code_dir / "Models"
        db_context_file = self.csharp_code_dir / "Data" / "AppDbContext.cs"

        if not models_dir.exists():
            print(f"Models directory not found at {models_dir}")
            return

        if not db_context_file.exists():
            print(f"AppDbContext file not found at {db_context_file}")
            return

        # Read the database context file
        db_context_content = db_context_file.read_text()

        # Get all model files in the directory
        all_model_files = list(models_dir.glob("*.cs"))
        model_file_dict = {}
        print(f"Found {len(all_model_files)} model files in {models_dir}")

        # Create a dictionary of model files with their names (without .cs extension)
        for model_file in all_model_files:
            model_name = model_file.stem  # Gets filename without extension
            model_file_dict[model_name.lower()] = model_file

        # Find base repository path
        base_repo_path = (
            self.csharp_code_dir / "Abstractions" / "Repositories" / "Repository.cs"
        )
        if base_repo_path.exists():
            # Store the path relative to the csharp_code_dir
            self.collected_data["entity_framework_analysis"]["base_repository_path"] = (
                str(base_repo_path.relative_to(self.csharp_code_dir))
            )
            print(
                f"Found base repository at {self.collected_data['entity_framework_analysis']['base_repository_path']}"
            )

        # For each table, look for a matching model file
        for table in self.tables:
            table_name = table["name"]
            full_table_name = table["full_name"]

            # Try different name transformations
            possible_model_names = [
                table_name,  # Exact match
                (
                    table_name[:-1] if table_name.endswith("s") else table_name
                ),  # Remove trailing 's'
                (
                    table_name + "s" if not table_name.endswith("s") else table_name
                ),  # Add trailing 's'
                table_name.replace("_", ""),  # Remove underscores
            ]

            print(f"Looking for model files for table {full_table_name} ({table_name})")

            # Check for each possible name
            found_model = False
            for possible_name in possible_model_names:
                if possible_name.lower() in model_file_dict:
                    model_file = model_file_dict[possible_name.lower()]
                    model_content = model_file.read_text()

                    # Only include if it seems to be a model class
                    if (
                        "public partial class" in model_content
                        or "public class" in model_content
                    ) and "{ get; set; }" in model_content:
                        model_name = model_file.stem

                        # Find DbSet in DbContext
                        db_set_name = self._find_db_set_name(
                            db_context_content, model_name
                        )

                        # Find repository folder
                        repository_folder_path = self._find_repository_folder(
                            model_name
                        )

                        # Extract properties from the model
                        properties = self._extract_properties(model_content)

                        model_info = {
                            "table_name": full_table_name,
                            # Store the path relative to the csharp_code_dir
                            "model_file_path": str(
                                model_file.relative_to(self.csharp_code_dir)
                            ),
                            "db_set_name": db_set_name,
                            "properties": properties,
                        }

                        # Store model_name and repository_folder_path temporarily for use in analyze_repository_files
                        model_info["_temp_model_name"] = model_name
                        model_info["_temp_repository_folder_path"] = (
                            repository_folder_path
                        )

                        self.collected_data["entity_framework_analysis"][
                            "related_models"
                        ].append(model_info)

                        found_model = True
                        print(
                            f"Found model {model_file.name} for table {full_table_name}"
                        )
                        break

            if not found_model:
                print(f"No model found for table {full_table_name}")

    def _find_db_set_name(self, db_context_content, model_name):
        """Find the DbSet property name for a model in the AppDbContext"""
        patterns = [
            rf"public\s+virtual\s+DbSet<(?:.*?\.)?{model_name}>\s+(\w+)\s*{{\s*get;\s*set;\s*}}",
            rf"public\s+DbSet<(?:.*?\.)?{model_name}>\s+(\w+)\s*{{\s*get;\s*set;\s*}}",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, db_context_content, re.IGNORECASE)
            if matches:
                return matches[0]

        return None

    def _find_repository_folder(self, model_name):
        """Find the repository folder path for a model"""
        repository_folder = self.csharp_code_dir / "Repositories" / model_name

        if repository_folder.exists() and repository_folder.is_dir():
            return str(repository_folder.relative_to(self.csharp_code_dir))

        return None

    def _extract_properties(self, model_content):
        """Extract properties from a model class"""
        properties = []
        # Enhanced property detection pattern to handle attributes and comments
        property_pattern = r"public\s+([^\s]+)\s+([^\s]+)\s*\{\s*get;\s*set;\s*\}"

        # Look for key attributes to identify primary keys
        key_pattern = (
            r"\[Key\]\s*\n\s*public\s+([^\s]+)\s+([^\s]+)\s*\{\s*get;\s*set;\s*\}"
        )
        foreign_key_pattern = r"\[ForeignKey\(\"([^\"]+)\"\)\]\s*\n\s*public\s+([^\s]+)\s+([^\s]+)\s*\{\s*get;\s*set;\s*\}"

        # Find primary keys
        primary_keys = []
        for match in re.finditer(key_pattern, model_content):
            prop_type, prop_name = match.groups()
            primary_keys.append(prop_name)
            properties.append(
                {"name": prop_name, "type": prop_type, "is_primary_key": True}
            )

        # Find foreign keys
        for match in re.finditer(foreign_key_pattern, model_content):
            reference, prop_type, prop_name = match.groups()
            properties.append(
                {
                    "name": prop_name,
                    "type": prop_type,
                    "is_foreign_key": True,
                    "references": reference,
                }
            )

        # Find regular properties
        for match in re.finditer(property_pattern, model_content):
            prop_type, prop_name = match.groups()
            # Skip properties already added as primary or foreign keys
            if not any(p["name"] == prop_name for p in properties):
                if not prop_name.startswith("//") and not prop_type.startswith("//"):
                    properties.append(
                        {
                            "name": prop_name,
                            "type": prop_type,
                            "is_primary_key": prop_name in primary_keys,
                        }
                    )

        return properties

    def analyze_repository_files(self):
        """Analyze the repository files related to the models"""
        print("Analyzing repository files...")

        # Update repository information for each related model
        for model_data in self.collected_data["entity_framework_analysis"][
            "related_models"
        ]:
            model_name = model_data.pop(
                "_temp_model_name"
            )  # Remove temporary field after using it
            repository_folder_path = model_data.pop(
                "_temp_repository_folder_path"
            )  # Remove temporary field after using it

            if repository_folder_path:
                repo_folder = self.csharp_code_dir / repository_folder_path

                # Check for repository interface
                interface_file = repo_folder / f"I{model_name}Repository.cs"
                if interface_file.exists():
                    model_data["repository_interface_path"] = str(
                        interface_file.relative_to(self.csharp_code_dir)
                    )

                    # Extract custom methods from the interface
                    interface_content = interface_file.read_text()
                    custom_methods = self._extract_custom_methods(interface_content)
                    if custom_methods:
                        model_data["custom_repository_methods"] = custom_methods

                # Check for repository implementation
                implementation_file = repo_folder / f"{model_name}Repository.cs"
                if implementation_file.exists():
                    model_data["repository_implementation_path"] = str(
                        implementation_file.relative_to(self.csharp_code_dir)
                    )

                # Check for unit of work interface
                unit_of_work_interface_file = (
                    repo_folder / f"I{model_name}UnitOfWork.cs"
                )
                if unit_of_work_interface_file.exists():
                    model_data["unit_of_work_interface_path"] = str(
                        unit_of_work_interface_file.relative_to(self.csharp_code_dir)
                    )

                # Check for unit of work implementation
                unit_of_work_file = repo_folder / f"UnitOfWork.{model_name}.cs"
                if unit_of_work_file.exists():
                    model_data["unit_of_work_path"] = str(
                        unit_of_work_file.relative_to(self.csharp_code_dir)
                    )

        print("Repository analysis completed")

    def _extract_custom_methods(self, interface_content):
        """Extract custom methods from a repository interface"""
        # Pattern to find method signatures in interface
        method_pattern = r"(?:Task<.*?>|void|Task|.*?)\s+(\w+)\s*\((.*?)\);"

        methods = []
        for match in re.finditer(method_pattern, interface_content):
            method_name, parameters = match.groups()

            # Skip common repository methods that are inherited
            if method_name in [
                "GetByIdAsync",
                "GetAllAsync",
                "FindAsync",
                "AnyAsync",
                "CountAsync",
                "FirstOrDefaultAsync",
                "GetQueryable",
                "AddAsync",
                "AddRangeAsync",
                "UpdateAsync",
                "UpdateRangeAsync",
                "DeleteAsync",
                "DeleteRangeAsync",
                "SaveChangesAsync",
            ]:
                continue

            # Parse parameters
            param_list = []
            if parameters.strip():
                param_parts = parameters.split(",")
                for part in param_parts:
                    part = part.strip()
                    if part:
                        param_type = " ".join(part.split()[:-1])
                        param_name = part.split()[-1]
                        param_list.append({"type": param_type, "name": param_name})

            # Add method to list
            method_info = {"name": method_name, "parameters": param_list}
            methods.append(method_info)

        return methods

    def save_report(self):
        """Save the collected data as a JSON report"""
        output_file = self.output_dir / f"{self.procedure_name}_ef_analysis.json"

        with open(output_file, "w") as f:
            json.dump(self.collected_data, f, indent=2)

        print(f"Entity Framework analysis report saved to {output_file}")


def analyze_csharp_dependencies(procedure_name, project_path):
    """Analyze C# dependencies for a procedure and create an ef_analysis.json file"""
    print(f"\nStarting C# dependency analysis for procedure: {procedure_name}")

    # Create analyzer for this procedure
    analyzer = EntityFrameworkAnalyzer(procedure_name, project_path)

    # Run analysis (tables will be extracted from SQL)
    result = analyzer.analyze()

    if result:
        print(f"C# dependency analysis completed for {procedure_name}")
        ef_analysis_path = os.path.join(
            project_path,
            "analysis",
            procedure_name,
            f"{procedure_name}_ef_analysis.json",
        )
        print(f"Analysis file saved to: {ef_analysis_path}")
        return True
    else:
        print(f"C# dependency analysis failed or skipped for {procedure_name}")
        return False


def run_csharp_dependency_analysis(project_path):
    """CLI menu function to select and analyze procedures"""
    print("=== C# Dependency Analysis ===")

    # Get all procedure folders from the sql_raw directory
    procedures = []
    sql_raw_dir = os.path.join(project_path, "sql_raw")

    if os.path.exists(sql_raw_dir):
        procedures = [
            folder
            for folder in os.listdir(sql_raw_dir)
            if os.path.isdir(os.path.join(sql_raw_dir, folder))
        ]

    if not procedures:
        print(f"No procedures found in {sql_raw_dir}")
        return

    # Display menu
    print("\nAvailable procedures:")
    for i, proc in enumerate(procedures):
        print(f"{i+1}. {proc}")
    print(f"{len(procedures)+1}. Analyze all procedures")
    print(f"{len(procedures)+2}. Return to main menu")

    # Get user selection
    try:
        choice = int(input("\nSelect a procedure to analyze (enter number): "))

        if 1 <= choice <= len(procedures):
            # Analyze single procedure
            procedure = procedures[choice - 1]
            analyze_csharp_dependencies(procedure, project_path)
            return

        elif choice == len(procedures) + 1:
            # Analyze all procedures
            completed = 0
            total = len(procedures)

            for procedure in procedures:
                print(f"\nProcessing {procedure} ({completed+1}/{total})...")
                analyze_csharp_dependencies(procedure, project_path)
                completed += 1

            print(f"\nC# dependency analysis completed for all {completed} procedures.")
            return

        elif choice == len(procedures) + 2:
            print("Returning to main menu...")
            return

        else:
            print("Invalid choice. Please try again.")
            return

    except ValueError:
        print("Please enter a valid number.")
        return

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return


if __name__ == "__main__":
    # For testing standalone execution
    project_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "output",
        "DemoDatabase",
    )
    run_csharp_dependency_analysis(project_path)
