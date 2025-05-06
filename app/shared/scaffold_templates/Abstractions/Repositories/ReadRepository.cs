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
    /// Generic repository implementation for read-only operations
    /// </summary>
    /// <typeparam name="T">Entity type</typeparam>
    public class ReadRepository<T> : IReadRepository<T> where T : class
    {
        protected readonly AppDbContext _context;
        protected readonly DbSet<T> _dbSet;

        /// <summary>
        /// Initializes a new instance of the ReadRepository class
        /// </summary>
        /// <param name="context">Database context</param>
        public ReadRepository(AppDbContext context)
        {
            _context = context ?? throw new ArgumentNullException(nameof(context));
            _dbSet = context.Set<T>();
        }

        /// <inheritdoc/>
        public virtual async Task<T?> GetByIdAsync(object id)
        {
            return await _dbSet.FindAsync(id);
        }

        /// <inheritdoc/>
        public virtual async Task<IEnumerable<T>> GetAllAsync()
        {
            return await _dbSet.ToListAsync();
        }

        /// <inheritdoc/>
        public virtual async Task<IEnumerable<T>> FindAsync(Expression<Func<T, bool>> predicate)
        {
            return await _dbSet.Where(predicate).ToListAsync();
        }

        /// <inheritdoc/>
        public virtual async Task<IEnumerable<T>> FindAsync(Expression<Func<T, bool>> predicate, params Expression<Func<T, object>>[] includeProperties)
        {
            IQueryable<T> query = _dbSet;
            
            foreach (var includeProperty in includeProperties)
            {
                query = query.Include(includeProperty);
            }
            
            return await query.Where(predicate).ToListAsync();
        }

        /// <inheritdoc/>
        public virtual async Task<bool> AnyAsync(Expression<Func<T, bool>> predicate)
        {
            return await _dbSet.AnyAsync(predicate);
        }

        /// <inheritdoc/>
        public virtual async Task<int> CountAsync(Expression<Func<T, bool>>? predicate = null)
        {
            if (predicate == null)
            {
                return await _dbSet.CountAsync();
            }
            
            return await _dbSet.CountAsync(predicate);
        }

        /// <inheritdoc/>
        public virtual async Task<T?> FirstOrDefaultAsync(Expression<Func<T, bool>> predicate)
        {
            return await _dbSet.FirstOrDefaultAsync(predicate);
        }

        /// <inheritdoc/>
        public virtual IQueryable<T> GetQueryable(params Expression<Func<T, object>>[] includeProperties)
        {
            IQueryable<T> query = _dbSet;
            
            foreach (var includeProperty in includeProperties)
            {
                query = query.Include(includeProperty);
            }
            
            return query;
        }
    }
}