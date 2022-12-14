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

    public EntityJsonHelper<TEntity> JsonHelper => _jsonHelper;

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

    public TEntity GetByKey(string key)
    {
        var result = _table.Select<TEntity>(_dbConnection, null, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key));
        return result.Single();
    }

    public string Create(JsonElement jsonElement)
    {
        var insertClauses = _jsonHelper.ConvertJsonElementToInsertClauses(jsonElement);
        var key = _table.Insert(_dbConnection, insertClauses);
        return (string)key;
    }
}
