namespace sql2code.Abstractions.Repositories
{
    /// <summary>
    /// Generic repository interface combining read and write operations
    /// </summary>
    /// <typeparam name="TEntity">Entity type</typeparam>
    public interface IRepository<TEntity> : IReadRepository<TEntity>, IWriteRepository<TEntity> where TEntity : class
    {
        // This interface combines both read and write operations
        // Additional methods specific to the combined repository can be added here
    }
}