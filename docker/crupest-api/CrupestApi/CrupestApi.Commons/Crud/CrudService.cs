using System.Data;
using Dapper;

namespace CrupestApi.Commons.Crud;

[Flags]
public enum UpdateBehavior
{
    None = 0,
    SaveNull = 1
}

public class CrudService<TEntity> : IDisposable where TEntity : class
{
    protected readonly TableInfo _table;
    protected readonly string? _connectionName;
    protected readonly IDbConnection _dbConnection;
    private readonly bool _shouldDisposeConnection;
    private readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, ILoggerFactory loggerFactory)
    {
        _connectionName = GetConnectionName();
        _table = tableInfoFactory.Get(typeof(TEntity));
        _dbConnection = dbConnectionFactory.Get(_connectionName);
        _shouldDisposeConnection = dbConnectionFactory.ShouldDisposeConnection;
        _logger = loggerFactory.CreateLogger<CrudService<TEntity>>();

        CheckDatabase(_dbConnection);
    }

    protected virtual string GetConnectionName()
    {
        return typeof(TEntity).Name;
    }

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
        if (_shouldDisposeConnection)
            _dbConnection.Dispose();
    }

    public List<TEntity> GetAll()
    {
        var result = _table.Select<TEntity>(_dbConnection, null);
        return result;
    }

    public TEntity GetByKey(object key)
    {
        var result = _table.Select<TEntity>(_dbConnection, null, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key)).SingleOrDefault();
        if (result is null)
        {
            throw new EntityNotExistException("Required entity not found.");
        }
        return result;
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

    public object Create(TEntity entity)
    {
        var insertClause = ConvertEntityToInsertClauses(entity);
        var key = _table.Insert(_dbConnection, insertClause);
        return key;
    }

    public IUpdateClause ConvertEntityToUpdateClauses(TEntity entity, UpdateBehavior behavior)
    {
        var result = UpdateClause.Create();
        var saveNull = behavior.HasFlag(UpdateBehavior.SaveNull);
        foreach (var column in _table.PropertyColumns)
        {
            var value = column.PropertyInfo!.GetValue(entity);
            if (!saveNull && value is null) continue;
            result.Add(column.ColumnName, value);
        }
        return result;
    }

    public void UpdateByKey(object key, TEntity entity, UpdateBehavior behavior)
    {
        var affectedCount = _table.Update(_dbConnection, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key),
            ConvertEntityToUpdateClauses(entity, behavior));
        if (affectedCount == 0)
        {
            throw new EntityNotExistException("Required entity not found.");
        }
    }

    public bool DeleteByKey(object key)
    {
        return _table.Delete(_dbConnection, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key)) == 1;
    }
}
