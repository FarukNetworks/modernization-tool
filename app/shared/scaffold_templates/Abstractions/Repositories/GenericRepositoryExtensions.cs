using Microsoft.Extensions.DependencyInjection;
using System;
using System.Linq;
using System.Reflection;

namespace sql2code.Abstractions.Repositories
{
    /// <summary>
    /// Generic extension methods for repository service registration
    /// </summary>
    public static class GenericRepositoryExtensions
    {
        /// <summary>
        /// Adds entity-specific repository services to the specified IServiceCollection
        /// </summary>
        /// <typeparam name="TEntity">Entity type</typeparam>
        /// <typeparam name="TRepository">Repository interface type</typeparam>
        /// <typeparam name="TRepositoryImpl">Repository implementation type</typeparam>
        public static IServiceCollection AddEntityServices<TEntity, TRepository, TRepositoryImpl>(
            this IServiceCollection services)
            where TEntity : class
            where TRepository : class, IRepository<TEntity>
            where TRepositoryImpl : class, TRepository
        {
            services.AddScoped<TRepository, TRepositoryImpl>();

            return services;
        }

        /// <summary>
        /// Adds all repository services for the application
        /// </summary>
        public static IServiceCollection AddAllRepositoryServices(this IServiceCollection services)
        {
            // Register core repositories
            services.AddRepositoryServices();

            // Get the assembly containing our repositories
            var assembly = typeof(GenericRepositoryExtensions).Assembly;

            Console.WriteLine($"Scanning assembly: {assembly.FullName}");

            // Find all repository implementations
            var repositoryTypes = assembly.GetTypes()
                .Where(t => t.IsClass && !t.IsAbstract && t.Name.EndsWith("Repository") &&
                           t.Name != "Repository" && t.Name != "ReadRepository" && t.Name != "WriteRepository")
                .ToList();

            Console.WriteLine($"Found {repositoryTypes.Count} repository implementations");

            foreach (var repositoryImpl in repositoryTypes)
            {
                Console.WriteLine($"Processing repository: {repositoryImpl.FullName}");

                // Find the corresponding interface
                var repositoryInterface = assembly.GetTypes()
                    .FirstOrDefault(t => t.IsInterface && t.Name == "I" + repositoryImpl.Name);

                if (repositoryInterface != null)
                {
                    Console.WriteLine($"Registering {repositoryInterface.Name} -> {repositoryImpl.Name}");

                    // Register the repository directly
                    services.AddScoped(repositoryInterface, repositoryImpl);
                }
                else
                {
                    Console.WriteLine($"Warning: Could not find interface for {repositoryImpl.Name}");
                }
            }

            return services;
        }
    }
}