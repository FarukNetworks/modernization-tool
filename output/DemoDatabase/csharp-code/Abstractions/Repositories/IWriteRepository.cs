using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace sql2code.Abstractions.Repositories
{
    /// <summary>
    /// Generic repository interface for write operations
    /// </summary>
    /// <typeparam name="TEntity">Entity type</typeparam>
    public interface IWriteRepository<TEntity> where TEntity : class
    {
        /// <summary>
        /// Adds a new entity
        /// </summary>
        /// <param name="entity">Entity to add</param>
        /// <returns>Added entity</returns>
        Task<TEntity> AddAsync(TEntity entity);
        
        /// <summary>
        /// Adds a collection of entities
        /// </summary>
        /// <param name="entities">Entities to add</param>
        /// <returns>Added entities</returns>
        Task<IEnumerable<TEntity>> AddRangeAsync(IEnumerable<TEntity> entities);
        
        /// <summary>
        /// Updates an existing entity
        /// </summary>
        /// <param name="entity">Entity to update</param>
        /// <returns>Updated entity</returns>
        Task<TEntity> UpdateAsync(TEntity entity);
        
        /// <summary>
        /// Updates a collection of entities
        /// </summary>
        /// <param name="entities">Entities to update</param>
        /// <returns>Updated entities</returns>
        Task<IEnumerable<TEntity>> UpdateRangeAsync(IEnumerable<TEntity> entities);
        
        /// <summary>
        /// Deletes an entity
        /// </summary>
        /// <param name="entity">Entity to delete</param>
        /// <returns>True if entity was deleted, otherwise false</returns>
        Task<bool> DeleteAsync(TEntity entity);
        
        /// <summary>
        /// Deletes an entity by ID
        /// </summary>
        /// <param name="id">ID of entity to delete</param>
        /// <returns>True if entity was deleted, otherwise false</returns>
        Task<bool> DeleteAsync(object id);
        
        /// <summary>
        /// Deletes a collection of entities
        /// </summary>
        /// <param name="entities">Entities to delete</param>
        /// <returns>True if all entities were deleted, otherwise false</returns>
        Task<bool> DeleteRangeAsync(IEnumerable<TEntity> entities);
        
        /// <summary>
        /// Saves changes to the database
        /// </summary>
        /// <returns>Number of state entries written to the database</returns>
        Task<int> SaveChangesAsync();
    }
}