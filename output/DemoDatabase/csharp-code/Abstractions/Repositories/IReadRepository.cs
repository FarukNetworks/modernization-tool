using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Threading.Tasks;

namespace sql2code.Abstractions.Repositories
{
    /// <summary>
    /// Generic repository interface for read-only operations
    /// </summary>
    /// <typeparam name="T">Entity type</typeparam>
    public interface IReadRepository<T> where T : class
    {
        /// <summary>
        /// Gets an entity by its ID
        /// </summary>
        /// <param name="id">Entity ID</param>
        /// <returns>Entity or null if not found</returns>
        Task<T?> GetByIdAsync(object id);
        
        /// <summary>
        /// Gets all entities of type T
        /// </summary>
        /// <returns>Collection of all entities</returns>
        Task<IEnumerable<T>> GetAllAsync();
        
        /// <summary>
        /// Gets entities matching the specified predicate
        /// </summary>
        /// <param name="predicate">Filter expression</param>
        /// <returns>Filtered collection of entities</returns>
        Task<IEnumerable<T>> FindAsync(Expression<Func<T, bool>> predicate);
        
        /// <summary>
        /// Gets entities matching the specified predicate
        /// </summary>
        /// <param name="predicate">Filter expression</param>
        /// <param name="includeProperties">Related entities to include</param>
        /// <returns>Filtered collection of entities with included properties</returns>
        Task<IEnumerable<T>> FindAsync(Expression<Func<T, bool>> predicate, params Expression<Func<T, object>>[] includeProperties);
        
        /// <summary>
        /// Checks if any entity matches the specified predicate
        /// </summary>
        /// <param name="predicate">Filter expression</param>
        /// <returns>True if matching entity exists, otherwise false</returns>
        Task<bool> AnyAsync(Expression<Func<T, bool>> predicate);
        
        /// <summary>
        /// Counts entities matching the specified predicate
        /// </summary>
        /// <param name="predicate">Filter expression</param>
        /// <returns>Count of matching entities</returns>
        Task<int> CountAsync(Expression<Func<T, bool>>? predicate = null);
        
        /// <summary>
        /// Gets the first entity matching the specified predicate or default value if not found
        /// </summary>
        /// <param name="predicate">Filter expression</param>
        /// <returns>First matching entity or default value</returns>
        Task<T?> FirstOrDefaultAsync(Expression<Func<T, bool>> predicate);
        
        /// <summary>
        /// Gets a queryable for the entity type with optional includes
        /// </summary>
        /// <param name="includeProperties">Related entities to include</param>
        /// <returns>Queryable for further operations</returns>
        IQueryable<T> GetQueryable(params Expression<Func<T, object>>[] includeProperties);
    }
}