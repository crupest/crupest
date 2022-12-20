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

    public CrudService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, EntityJsonHelper<TEntity> jsonHelper, ILoggerFactory loggerFactory)
    {
        _connectionName = GetConnectionName();
        _table = tableInfoFactory.Get(typeof(TEntity));
        _dbConnection = dbConnectionFactory.Get(_connectionName);
        _jsonHelper = jsonHelper;
        _logger = loggerFactory.CreateLogger<CrudService<TEntity>>();

        CheckDatabase(_dbConnection);
    }

    protected virtual string GetConnectionName()
    {
        return typeof(TEntity).Name;
    }

    public EntityJsonHelper<TEntity> JsonHelper => _jsonHelper;

    protected virtual void CheckDatabase(IDbConnection dbConnection)
    {
        if (!_table.CheckExistence(dbConnection))
        {
            DoInitializeDatabase(dbConnection);
        }
    }

    protected virtual void DoInitializeDatabase(IDbConnection connection)
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

    public TEntity GetByKey(object key)
    {
        var result = _table.Select<TEntity>(_dbConnection, null, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key));
        return result.Single();
    }

    public IInsertClause ConvertEntityToInsertClauses(TEntity entity)
    {
        var result = new InsertClause();
        foreach (var column in _table.PropertyColumns)
        {
            var value = column.PropertyInfo!.GetValue(entity);
            result.Add(column.ColumnName, value);
        }
        return result;
    }

    public string Create(TEntity entity)
    {
        var insertClause = ConvertEntityToInsertClauses(entity);
        var key = _table.Insert(_dbConnection, insertClause);
        return (string)key;
    }

    public string Create(JsonElement jsonElement)
    {
        var insertClauses = _jsonHelper.ConvertJsonElementToInsertClauses(jsonElement);
        var key = _table.Insert(_dbConnection, insertClauses);
        return (string)key;
    }

    public void UpdateByKey(object key, JsonElement jsonElement)
    {
        var updateClauses = _jsonHelper.ConvertJsonElementToUpdateClause(jsonElement);
        _table.Update(_dbConnection, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key), updateClauses);
    }

    public void DeleteByKey(object key)
    {
        _table.Delete(_dbConnection, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key));
    }
}
