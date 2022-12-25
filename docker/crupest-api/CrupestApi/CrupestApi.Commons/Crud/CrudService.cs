using System.Data;
using CrupestApi.Commons.Crud.Migrations;

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
    private IDatabaseMigrator _migrator;
    private readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, IDatabaseMigrator migrator, ILoggerFactory loggerFactory)
    {
        _connectionName = GetConnectionName();
        _table = tableInfoFactory.Get(typeof(TEntity));
        _dbConnection = dbConnectionFactory.Get(_connectionName);
        _shouldDisposeConnection = dbConnectionFactory.ShouldDisposeConnection;
        _migrator = migrator;
        _logger = loggerFactory.CreateLogger<CrudService<TEntity>>();

        if (migrator.NeedMigrate(_dbConnection, _table))
        {
            _logger.LogInformation($"Entity {_table.TableName} needs migration.");
            if (migrator.CanAutoMigrate(_dbConnection, _table))
            {
                _logger.LogInformation($"Entity {_table.TableName} can be auto migrated.");
                migrator.AutoMigrate(_dbConnection, _table);
                AfterMigrate(_dbConnection, _table, loggerFactory);
            }
            else
            {
                _logger.LogInformation($"Entity {_table.TableName} can not be auto migrated.");
                throw new Exception($"Entity {_table.TableName} needs migration but can not be auto migrated.");
            }
        }
        else
        {
            _logger.LogInformation($"Entity {_table.TableName} does not need migration.");
        }
    }

    protected virtual string GetConnectionName()
    {
        return typeof(TEntity).Name;
    }

    protected virtual void AfterMigrate(IDbConnection dbConnection, TableInfo tableInfo, ILoggerFactory loggerFactory)
    {

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

    public int GetCount()
    {
        var result = _table.SelectCount(_dbConnection);
        return result;
    }

    public TEntity GetByKey(object key)
    {
        var result = _table.Select<TEntity>(_dbConnection, null, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key)).SingleOrDefault();
        if (result is null)
        {
            throw new EntityNotExistException($"Required entity for key {key} not found.");
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
        _table.Insert(_dbConnection, insertClause, out var key);
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

    // Return new key.
    public object UpdateByKey(object key, TEntity entity, UpdateBehavior behavior = UpdateBehavior.None)
    {
        var affectedCount = _table.Update(_dbConnection, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key),
            ConvertEntityToUpdateClauses(entity, behavior), out var newKey);
        if (affectedCount == 0)
        {
            throw new EntityNotExistException($"Required entity for key {key} not found.");
        }
        return newKey ?? key;
    }

    public bool DeleteByKey(object key)
    {
        return _table.Delete(_dbConnection, WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key)) == 1;
    }
}
