using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using sql2code.Data;

namespace sql2code.Abstractions.Repositories
{
    /// <summary>
    /// Generic repository implementation for keyless entities 
    /// (entities that don't have a primary key defined)
    /// </summary>
    /// <typeparam name="TEntity">Entity type</typeparam>
    public class KeylessRepository<TEntity> : ReadRepository<TEntity>, IRepository<TEntity> where TEntity : class
    {
        protected new readonly AppDbContext _context;
        protected new readonly DbSet<TEntity> _dbSet;

        /// <summary>
        /// Initializes a new instance of the KeylessRepository class
        /// </summary>
        /// <param name="context">Database context</param>
        public KeylessRepository(AppDbContext context) : base(context)
        {
            _context = context ?? throw new ArgumentNullException(nameof(context));
            _dbSet = _context.Set<TEntity>();
        }

        #region Write Operations

        /// <inheritdoc/>
        public virtual async Task<TEntity> AddAsync(TEntity entity)
        {
            if (entity == null)
            {
                throw new ArgumentNullException(nameof(entity));
            }

            await _dbSet.AddAsync(entity);
            await _context.SaveChangesAsync();
            return entity;
        }

        /// <inheritdoc/>
        public virtual async Task<IEnumerable<TEntity>> AddRangeAsync(IEnumerable<TEntity> entities)
        {
            if (entities == null)
            {
                throw new ArgumentNullException(nameof(entities));
            }

            await _dbSet.AddRangeAsync(entities);
            await _context.SaveChangesAsync();
            return entities;
        }

        /// <inheritdoc/>
        public virtual async Task<TEntity> UpdateAsync(TEntity entity)
        {
            if (entity == null)
            {
                throw new ArgumentNullException(nameof(entity));
            }

            _dbSet.Update(entity);
            await _context.SaveChangesAsync();
            return entity;
        }

        /// <inheritdoc/>
        public virtual async Task<IEnumerable<TEntity>> UpdateRangeAsync(IEnumerable<TEntity> entities)
        {
            if (entities == null)
            {
                throw new ArgumentNullException(nameof(entities));
            }

            _dbSet.UpdateRange(entities);
            await _context.SaveChangesAsync();
            return entities;
        }

        /// <inheritdoc/>
        public virtual async Task<bool> DeleteAsync(TEntity entity)
        {
            if (entity == null)
            {
                throw new ArgumentNullException(nameof(entity));
            }

            _dbSet.Remove(entity);
            await _context.SaveChangesAsync();
            return true;
        }

        /// <inheritdoc/>
        public virtual Task<bool> DeleteAsync(object id)
        {
            throw new NotSupportedException("DeleteAsync by ID is not supported for keyless entities. Use DeleteAsync(entity) instead.");
        }

        /// <inheritdoc/>
        public virtual async Task<bool> DeleteRangeAsync(IEnumerable<TEntity> entities)
        {
            if (entities == null)
            {
                throw new ArgumentNullException(nameof(entities));
            }

            _dbSet.RemoveRange(entities);
            await _context.SaveChangesAsync();
            return true;
        }

        /// <inheritdoc/>
        public async Task<int> SaveChangesAsync()
        {
            return await _context.SaveChangesAsync();
        }

        #endregion
    }
}