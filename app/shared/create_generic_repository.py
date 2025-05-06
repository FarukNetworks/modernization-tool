#!/usr/bin/env python3
"""
This script analyzes a .NET project with Entity Framework Core models and generates
a generic repository implementation. It examines the model classes and DbContext
to extract entity relationships and metadata, then creates the necessary repository files.

Usage:
    python create_generic_repository.py [project_path]

If no project_path is provided, it defaults to the current directory.
"""

import os
import re
import sys
from typing import Dict, List, Set, Tuple

def find_model_files(project_path: str) -> List[str]:
    """Find all model class files in the specified directory."""
    models_dir = os.path.join(project_path, "Models")
    if not os.path.exists(models_dir):
        print(f"Error: Models directory not found at {models_dir}")
        sys.exit(1)
    
    model_files = []
    for file in os.listdir(models_dir):
        if file.endswith(".cs"):
            model_files.append(os.path.join(models_dir, file))
    
    return model_files

def find_db_context_file(project_path: str) -> str:
    """Find the DbContext file in the project."""
    data_dir = os.path.join(project_path, "Data")
    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found at {data_dir}")
        sys.exit(1)
    
    for file in os.listdir(data_dir):
        if file.endswith("Context.cs"):
            return os.path.join(data_dir, file)
    
    print("Error: Unable to find DbContext file")
    sys.exit(1)

def analyze_model_file(file_path: str) -> Dict:
    """Analyze a model file to extract class name and properties."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract namespace
    namespace_match = re.search(r'namespace\s+([^;]+);', content)
    namespace = namespace_match.group(1) if namespace_match else "Unknown"
    
    # Extract class name
    class_match = re.search(r'public\s+partial\s+class\s+(\w+)', content)
    if not class_match:
        return None
    
    class_name = class_match.group(1)
    
    # Extract properties
    properties = []
    prop_matches = re.finditer(r'public\s+(?:virtual\s+)?([^\s]+)\s+(\w+)\s*{\s*get;\s*set;\s*}', content)
    for match in prop_matches:
        prop_type = match.group(1)
        prop_name = match.group(2)
        properties.append({"name": prop_name, "type": prop_type})
    
    # Extract navigation properties
    navigation_properties = []
    nav_matches = re.finditer(r'public\s+virtual\s+(?:ICollection<([^>]+)>|([^\s]+))\s+(\w+)\s*{\s*get;\s*set;\s*}', content)
    for match in nav_matches:
        collection_type = match.group(1)
        single_type = match.group(2)
        prop_name = match.group(3)
        
        if collection_type:
            navigation_properties.append({
                "name": prop_name, 
                "type": collection_type, 
                "is_collection": True
            })
        else:
            navigation_properties.append({
                "name": prop_name, 
                "type": single_type, 
                "is_collection": False
            })
    
    # Find primary key property
    primary_key = None
    common_id_patterns = [f"{class_name}Id", "Id"]
    
    for pattern in common_id_patterns:
        for prop in properties:
            if prop["name"] == pattern:
                primary_key = prop["name"]
                break
        if primary_key:
            break
    
    return {
        "namespace": namespace,
        "class_name": class_name,
        "properties": properties,
        "navigation_properties": navigation_properties,
        "primary_key": primary_key
    }

def analyze_db_context(file_path: str) -> Dict:
    """Analyze the DbContext file to extract entity sets and configurations."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract context name
    context_match = re.search(r'public\s+partial\s+class\s+(\w+)\s*:\s*DbContext', content)
    context_name = context_match.group(1) if context_match else "AppDbContext"
    
    # Extract namespace
    namespace_match = re.search(r'namespace\s+([^;]+);', content)
    namespace = namespace_match.group(1) if namespace_match else "Unknown"
    
    # Extract DbSet properties
    db_sets = []
    dbset_matches = re.finditer(r'public\s+virtual\s+DbSet<([^>]+)>\s+(\w+)\s*{\s*get;\s*set;\s*}', content)
    for match in dbset_matches:
        entity_type = match.group(1)
        prop_name = match.group(2)
        db_sets.append({"entity_type": entity_type, "property_name": prop_name})
    
    return {
        "namespace": namespace,
        "context_name": context_name,
        "db_sets": db_sets
    }

def generate_repository_interface(project_path: str, context_info: Dict) -> str:
    """Generate the code for the repository interface."""
    namespace = context_info['namespace'].replace("Data", "Repositories")
    
    interface_code = f"""using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using {context_info['namespace']};

namespace {namespace}
{{
    public interface IRepository<TEntity> where TEntity : class
    {{
        // Get all entities
        IQueryable<TEntity> GetAll();
        
        // Get entities with filtering
        IQueryable<TEntity> GetAll(Expression<Func<TEntity, bool>> predicate);
        
        // Get entity by id
        Task<TEntity> GetByIdAsync(object id);
        
        // Get entity with filtering
        Task<TEntity> GetFirstOrDefaultAsync(Expression<Func<TEntity, bool>> predicate);
        
        // Add entity
        Task AddAsync(TEntity entity);
        
        // Add multiple entities
        Task AddRangeAsync(IEnumerable<TEntity> entities);
        
        // Update entity
        void Update(TEntity entity);
        
        // Update multiple entities
        void UpdateRange(IEnumerable<TEntity> entities);
        
        // Remove entity
        void Remove(TEntity entity);
        
        // Remove by id
        Task RemoveByIdAsync(object id);
        
        // Remove multiple entities
        void RemoveRange(IEnumerable<TEntity> entities);
        
        // Save changes to database
        Task<int> SaveChangesAsync();
        
        // Check if any entity matches the condition
        Task<bool> AnyAsync(Expression<Func<TEntity, bool>> predicate);
        
        // Get count of entities matching condition
        Task<int> CountAsync(Expression<Func<TEntity, bool>> predicate);
    }}
}}
"""
    
    # Write the interface file
    interface_path = os.path.join(project_path, "Repositories", "IRepository.cs")
    os.makedirs(os.path.dirname(interface_path), exist_ok=True)
    
    with open(interface_path, 'w') as f:
        f.write(interface_code)
    
    return interface_path

def generate_repository_implementation(project_path: str, context_info: Dict) -> str:
    """Generate the code for the repository implementation."""
    namespace = context_info['namespace'].replace("Data", "Repositories")
    
    repository_code = f"""using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using {context_info['namespace']};

namespace {namespace}
{{
    public class Repository<TEntity> : IRepository<TEntity> where TEntity : class
    {{
        protected readonly {context_info['context_name']} _context;
        protected readonly DbSet<TEntity> _dbSet;

        public Repository({context_info['context_name']} context)
        {{
            _context = context;
            _dbSet = context.Set<TEntity>();
        }}

        public virtual IQueryable<TEntity> GetAll()
        {{
            return _dbSet;
        }}

        public virtual IQueryable<TEntity> GetAll(Expression<Func<TEntity, bool>> predicate)
        {{
            return _dbSet.Where(predicate);
        }}

        public virtual async Task<TEntity> GetByIdAsync(object id)
        {{
            return await _dbSet.FindAsync(id);
        }}

        public virtual async Task<TEntity> GetFirstOrDefaultAsync(Expression<Func<TEntity, bool>> predicate)
        {{
            return await _dbSet.FirstOrDefaultAsync(predicate);
        }}

        public virtual async Task AddAsync(TEntity entity)
        {{
            await _dbSet.AddAsync(entity);
        }}

        public virtual async Task AddRangeAsync(IEnumerable<TEntity> entities)
        {{
            await _dbSet.AddRangeAsync(entities);
        }}

        public virtual void Update(TEntity entity)
        {{
            _dbSet.Attach(entity);
            _context.Entry(entity).State = EntityState.Modified;
        }}

        public virtual void UpdateRange(IEnumerable<TEntity> entities)
        {{
            foreach (var entity in entities)
            {{
                Update(entity);
            }}
        }}

        public virtual void Remove(TEntity entity)
        {{
            if (_context.Entry(entity).State == EntityState.Detached)
            {{
                _dbSet.Attach(entity);
            }}
            _dbSet.Remove(entity);
        }}

        public virtual async Task RemoveByIdAsync(object id)
        {{
            TEntity entity = await GetByIdAsync(id);
            if (entity != null)
            {{
                Remove(entity);
            }}
        }}

        public virtual void RemoveRange(IEnumerable<TEntity> entities)
        {{
            _dbSet.RemoveRange(entities);
        }}

        public virtual async Task<int> SaveChangesAsync()
        {{
            return await _context.SaveChangesAsync();
        }}

        public virtual async Task<bool> AnyAsync(Expression<Func<TEntity, bool>> predicate)
        {{
            return await _dbSet.AnyAsync(predicate);
        }}

        public virtual async Task<int> CountAsync(Expression<Func<TEntity, bool>> predicate)
        {{
            return await _dbSet.CountAsync(predicate);
        }}
    }}
}}
"""
    
    # Write the repository implementation file
    repo_path = os.path.join(project_path, "Repositories", "Repository.cs")
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    
    with open(repo_path, 'w') as f:
        f.write(repository_code)
    
    return repo_path

def generate_unit_of_work_interface(project_path: str, context_info: Dict, model_infos: List[Dict]) -> str:
    """Generate the code for the unit of work interface."""
    namespace = context_info['namespace'].replace("Data", "Repositories")
    
    # Start with the interface declaration
    unit_of_work_interface = f"""using System;
using System.Threading.Tasks;
using {context_info['namespace']};

namespace {namespace}
{{
    public interface IUnitOfWork : IDisposable
    {{
        // Repositories
"""
    
    # Add repository properties for each entity
    for model_info in model_infos:
        if model_info and model_info['class_name'] and not model_info['class_name'].startswith("Vw"):  # Skip view models
            unit_of_work_interface += f"        IRepository<{model_info['namespace']}.{model_info['class_name']}> {model_info['class_name']}Repository {{ get; }}\n"
    
    # Add save method
    unit_of_work_interface += """
        // Save changes to database
        Task<int> SaveChangesAsync();
    }
}
"""
    
    # Write the unit of work interface file
    uow_interface_path = os.path.join(project_path, "Repositories", "IUnitOfWork.cs")
    os.makedirs(os.path.dirname(uow_interface_path), exist_ok=True)
    
    with open(uow_interface_path, 'w') as f:
        f.write(unit_of_work_interface)
    
    return uow_interface_path

def generate_unit_of_work_implementation(project_path: str, context_info: Dict, model_infos: List[Dict]) -> str:
    """Generate the code for the unit of work implementation."""
    namespace = context_info['namespace'].replace("Data", "Repositories")
    
    # Start with the class declaration
    unit_of_work_implementation = f"""using System;
using System.Threading.Tasks;
using {context_info['namespace']};

namespace {namespace}
{{
    public class UnitOfWork : IUnitOfWork
    {{
        private readonly {context_info['context_name']} _context;
        private bool _disposed = false;

        // Repository instances
"""
    
    # Add private fields for repositories
    for model_info in model_infos:
        if model_info and model_info['class_name'] and not model_info['class_name'].startswith("Vw"):  # Skip view models
            unit_of_work_implementation += f"        private IRepository<{model_info['namespace']}.{model_info['class_name']}> _{model_info['class_name'].lower()}Repository;\n"
    
    # Constructor
    unit_of_work_implementation += f"""
        public UnitOfWork({context_info['context_name']} context)
        {{
            _context = context;
        }}

        // Repository properties
"""
    
    # Add repository properties
    for model_info in model_infos:
        if model_info and model_info['class_name'] and not model_info['class_name'].startswith("Vw"):  # Skip view models
            unit_of_work_implementation += f"""        public IRepository<{model_info['namespace']}.{model_info['class_name']}> {model_info['class_name']}Repository
        {{
            get
            {{
                if (_{model_info['class_name'].lower()}Repository == null)
                {{
                    _{model_info['class_name'].lower()}Repository = new Repository<{model_info['namespace']}.{model_info['class_name']}>(this._context);
                }}
                return _{model_info['class_name'].lower()}Repository;
            }}
        }}
"""
    
    # Add save method and dispose
    unit_of_work_implementation += """
        public async Task<int> SaveChangesAsync()
        {
            return await _context.SaveChangesAsync();
        }

        protected virtual void Dispose(bool disposing)
        {
            if (!_disposed)
            {
                if (disposing)
                {
                    _context.Dispose();
                }
            }
            _disposed = true;
        }

        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }
    }
}
"""
    
    # Write the unit of work implementation file
    uow_path = os.path.join(project_path, "Repositories", "UnitOfWork.cs")
    os.makedirs(os.path.dirname(uow_path), exist_ok=True)
    
    with open(uow_path, 'w') as f:
        f.write(unit_of_work_implementation)
    
    return uow_path

def generate_service_registration(project_path: str, context_info: Dict) -> str:
    """Generate code to register the repositories in the DI container."""
    namespace = context_info['namespace'].replace("Data", "Repositories")
    
    service_registration_code = f"""using Microsoft.Extensions.DependencyInjection;
using {context_info['namespace']};
using {namespace};

namespace {context_info['namespace'].replace("Data", "Extensions")}
{{
    public static class RepositoryServiceExtensions
    {{
        public static IServiceCollection AddRepositories(this IServiceCollection services)
        {{
            services.AddScoped(typeof(IRepository<>), typeof(Repository<>));
            services.AddScoped<IUnitOfWork, UnitOfWork>();
            
            return services;
        }}
    }}
}}
"""
    
    # Write the service registration file
    service_path = os.path.join(project_path, "Extensions", "RepositoryServiceExtensions.cs")
    os.makedirs(os.path.dirname(service_path), exist_ok=True)
    
    with open(service_path, 'w') as f:
        f.write(service_registration_code)
    
    return service_path

def update_program_cs(project_path: str, context_info: Dict) -> None:
    """Update Program.cs to register repositories."""
    program_path = os.path.join(project_path, "Program.cs")
    
    if not os.path.exists(program_path):
        print(f"Warning: Program.cs not found at {program_path}")
        return
    
    with open(program_path, 'r') as f:
        content = f.read()
    
    # Add using statement
    extensions_namespace = context_info['namespace'].replace("Data", "Extensions")
    if f"using {extensions_namespace};" not in content:
        builder_line = "var builder = WebApplication.CreateBuilder(args);"
        if builder_line in content:
            content = content.replace(builder_line, f"using {extensions_namespace};\n\n{builder_line}")
    
    # Add registration call
    service_add_pattern = r'(builder\.Services\.AddDbContext<[^>]+>)'
    if "builder.Services.AddRepositories();" not in content and re.search(service_add_pattern, content):
        match = re.search(service_add_pattern, content)
        if match:
            db_context_line = match.group(0)
            content = content.replace(db_context_line, f"{db_context_line}\nbuilder.Services.AddRepositories();")
    
    with open(program_path, 'w') as f:
        f.write(content)

def main():
    # Get project path from argument or use default
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "/Users/sreckojarcevic/Documents/projects/crewai-workflow-transpiler/output/csharp-code"
    
    # Create directory for the repositories
    os.makedirs(os.path.join(project_path, "Repositories"), exist_ok=True)
    
    # Find model files and DbContext
    model_files = find_model_files(project_path)
    db_context_file = find_db_context_file(project_path)
    
    print(f"Found {len(model_files)} model files")
    print(f"Found DbContext file: {db_context_file}")
    
    # Analyze models
    model_infos = []
    for model_file in model_files:
        model_info = analyze_model_file(model_file)
        if model_info:
            model_infos.append(model_info)
    
    print(f"Analyzed {len(model_infos)} model classes")
    
    # Analyze DbContext
    context_info = analyze_db_context(db_context_file)
    print(f"Analyzed DbContext: {context_info['context_name']}")
    
    # Generate code
    interface_path = generate_repository_interface(project_path, context_info)
    print(f"Generated repository interface: {interface_path}")
    
    repo_path = generate_repository_implementation(project_path, context_info)
    print(f"Generated repository implementation: {repo_path}")
    
    uow_interface_path = generate_unit_of_work_interface(project_path, context_info, model_infos)
    print(f"Generated unit of work interface: {uow_interface_path}")
    
    uow_path = generate_unit_of_work_implementation(project_path, context_info, model_infos)
    print(f"Generated unit of work implementation: {uow_path}")
    
    service_path = generate_service_registration(project_path, context_info)
    print(f"Generated service registration: {service_path}")
    
    # Update Program.cs
    update_program_cs(project_path, context_info)
    print("Updated Program.cs to register repositories")
    
    print("\nGeneric repository implementation successfully created!")
    print("The following files were generated:")
    print(f"- {interface_path}")
    print(f"- {repo_path}")
    print(f"- {uow_interface_path}")
    print(f"- {uow_path}")
    print(f"- {service_path}")

if __name__ == "__main__":
    main()
