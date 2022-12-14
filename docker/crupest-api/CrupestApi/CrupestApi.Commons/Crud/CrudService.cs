using System.Data;
using System.Text.Json;
using Dapper;

namespace CrupestApi.Commons.Crud;

public class CrudService<TEntity> : IDisposable where TEntity : class
{
    protected readonly TableInfo _table;
    protected readonly string? _connectionName;
    protected readonly IDbConnection _dbConnection;
    protected readonly EntityJsonHelper<TEntity> _jsonHelper;
    private readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(string? connectionName, ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, EntityJsonHelper<TEntity> jsonHelper, ILoggerFactory loggerFactory)
    {
        _connectionName = connectionName;
        _table = tableInfoFactory.Get(typeof(TEntity));
        _dbConnection = dbConnectionFactory.Get(_connectionName);
        _jsonHelper = jsonHelper;
        _logger = loggerFactory.CreateLogger<CrudService<TEntity>>();

        if (!_table.CheckExistence(_dbConnection))
        {
            DoInitializeDatabase(_dbConnection);
        }
    }

    public virtual void DoInitializeDatabase(IDbConnection connection)
    {
        using var transaction = connection.BeginTransaction();
        connection.Execute(_table.GenerateCreateTableSql(), transaction: transaction);
        transaction.Commit();
    }

    public void Dispose()
    {
        _dbConnection.Dispose();
    }

    public List<TEntity> GetAll()
    {
        var result = _table.Select<TEntity>(_dbConnection, null);
        return result;
    }
}
