using Microsoft.Extensions.DependencyInjection;
using System;
using System.Linq;
using System.Reflection;

namespace sql2code.Abstractions.Repositories
{
    /// <summary>
    /// Extension methods for core repository service registration
    /// </summary>
    public static class RepositoryServiceExtensions
    {
        /// <summary>
        /// Adds core repository services to the specified IServiceCollection
        /// </summary>
        public static IServiceCollection AddRepositoryServices(this IServiceCollection services)
        {
            // Register generic repositories
            services.AddScoped(typeof(IReadRepository<>), typeof(ReadRepository<>));
            services.AddScoped(typeof(IWriteRepository<>), typeof(WriteRepository<>));
            services.AddScoped(typeof(IRepository<>), typeof(Repository<>));
            services.AddScoped(typeof(KeylessRepository<>));

            // Auto-register all specific repositories using assembly scanning
            var entryAssembly = Assembly.GetEntryAssembly();
            var repositoryTypes = entryAssembly?.GetTypes()
                .Where(t => !t.IsAbstract && !t.IsInterface && t.Name.EndsWith("Repository") &&
                           !t.Name.Equals("Repository") && !t.Name.Equals("ReadRepository") &&
                           !t.Name.Equals("WriteRepository") && !t.Name.Equals("KeylessRepository"))
                .ToList();

            if (repositoryTypes != null)
            {
                foreach (var repoType in repositoryTypes)
                {
                    // Find the interface that this repository implements
                    var interfaceType = repoType.GetInterfaces()
                        .FirstOrDefault(i => i.Name.EndsWith(repoType.Name) ||
                                            i.Name.Equals($"I{repoType.Name}"));

                    if (interfaceType != null)
                    {
                        // Register the repository with its interface
                        services.AddScoped(interfaceType, repoType);
                    }
                }
            }

            return services;
        }
    }
}