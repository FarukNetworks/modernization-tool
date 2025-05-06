using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Threading.Tasks;
using sql2code.Data;

namespace sql2code.Abstractions.Repositories
{
    /// <summary>
    /// Generic repository implementation combining read and write operations
    /// </summary>
    /// <typeparam name="TEntity">Entity type</typeparam>
    public class Repository<TEntity> : ReadRepository<TEntity>, IRepository<TEntity> where TEntity : class
    {
        private readonly ReadRepository<TEntity> _readRepository;
        private readonly WriteRepository<TEntity> _writeRepository;

        /// <summary>
        /// Initializes a new instance of the Repository class
        /// </summary>
        /// <param name="context">Database context</param>
        public Repository(AppDbContext context) : base(context)
        {
            _readRepository = new ReadRepository<TEntity>(context);
            _writeRepository = new WriteRepository<TEntity>(context);
        }

        #region Read Operations

        /// <inheritdoc/>
        public override async Task<TEntity?> GetByIdAsync(object id)
        {
            return await _readRepository.GetByIdAsync(id);
        }

        /// <inheritdoc/>
        public override async Task<IEnumerable<TEntity>> GetAllAsync()
        {
            return await _readRepository.GetAllAsync();
        }

        /// <inheritdoc/>
        public override async Task<IEnumerable<TEntity>> FindAsync(Expression<Func<TEntity, bool>> predicate)
        {
            return await _readRepository.FindAsync(predicate);
        }

        /// <inheritdoc/>
        public override async Task<IEnumerable<TEntity>> FindAsync(Expression<Func<TEntity, bool>> predicate, params Expression<Func<TEntity, object>>[] includeProperties)
        {
            return await _readRepository.FindAsync(predicate, includeProperties);
        }

        /// <inheritdoc/>
        public override async Task<bool> AnyAsync(Expression<Func<TEntity, bool>> predicate)
        {
            return await _readRepository.AnyAsync(predicate);
        }

        /// <inheritdoc/>
        public override async Task<int> CountAsync(Expression<Func<TEntity, bool>>? predicate = null)
        {
            return await _readRepository.CountAsync(predicate);
        }

        /// <inheritdoc/>
        public override async Task<TEntity?> FirstOrDefaultAsync(Expression<Func<TEntity, bool>> predicate)
        {
            return await _readRepository.FirstOrDefaultAsync(predicate);
        }

        /// <inheritdoc/>
        public override IQueryable<TEntity> GetQueryable(params Expression<Func<TEntity, object>>[] includeProperties)
        {
            return _readRepository.GetQueryable(includeProperties);
        }

        #endregion

        #region Write Operations

        /// <inheritdoc/>
        public virtual async Task<TEntity> AddAsync(TEntity entity)
        {
            return await _writeRepository.AddAsync(entity);
        }

        /// <inheritdoc/>
        public virtual async Task<IEnumerable<TEntity>> AddRangeAsync(IEnumerable<TEntity> entities)
        {
            return await _writeRepository.AddRangeAsync(entities);
        }

        /// <inheritdoc/>
        public virtual async Task<TEntity> UpdateAsync(TEntity entity)
        {
            return await _writeRepository.UpdateAsync(entity);
        }

        /// <inheritdoc/>
        public virtual async Task<IEnumerable<TEntity>> UpdateRangeAsync(IEnumerable<TEntity> entities)
        {
            return await _writeRepository.UpdateRangeAsync(entities);
        }

        /// <inheritdoc/>
        public virtual async Task<bool> DeleteAsync(TEntity entity)
        {
            return await _writeRepository.DeleteAsync(entity);
        }

        /// <inheritdoc/>
        public virtual async Task<bool> DeleteAsync(object id)
        {
            return await _writeRepository.DeleteAsync(id);
        }

        /// <inheritdoc/>
        public virtual async Task<bool> DeleteRangeAsync(IEnumerable<TEntity> entities)
        {
            return await _writeRepository.DeleteRangeAsync(entities);
        }

        /// <inheritdoc/>
        public async Task<int> SaveChangesAsync()
        {
            return await _writeRepository.SaveChangesAsync();
        }

        #endregion
    }
}