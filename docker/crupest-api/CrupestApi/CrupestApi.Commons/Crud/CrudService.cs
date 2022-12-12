using System.Data;
using System.Text.Json;
using Dapper;

namespace CrupestApi.Commons.Crud;

// TODO: Register this.
public class CrudService<TEntity> : IDisposable where TEntity : class
{
    protected readonly TableInfo _table;
    protected readonly string? _connectionName;
    protected readonly IDbConnection _dbConnection;
    protected readonly EntityJsonHelper _jsonHelper;
    private readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(string? connectionName, ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, ILoggerFactory loggerFactory)
    {
        _connectionName = connectionName;
        _table = tableInfoFactory.Get(typeof(TEntity));
        _dbConnection = dbConnectionFactory.Get(_connectionName);
        _jsonHelper = new EntityJsonHelper(_table);
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

    public List<TEntity> Select(IWhereClause? filter)
    {
        return _table.Select<TEntity>(_dbConnection, null, filter).ToList();
    }

    public bool Exists(IWhereClause? filter)
    {
        return _table.SelectCount(_dbConnection, filter) > 0;
    }

    public int Count(IWhereClause? filter)
    {
        return _table.SelectCount(_dbConnection, filter);
    }

    // Return the key.
    public object Insert(IInsertClause insertClause)
    {
        return _table.Insert(_dbConnection, insertClause);
    }

    // Return the key. TODO: Continue here.
    public object Insert(TEntity entity)
    {
        return _table.Insert(_dbConnection, );
    }

    public int Update(IUpdateClause updateClause, IWhereClause? filter)
    {
        return _table.Update(_dbConnection, filter, updateClause);
    }

    public int Delete(IWhereClause? filter)
    {
        return _table.Delete(_dbConnection, filter);
    }

    public TEntity SelectByKey(object key)
    {
        return Select(WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key)).Single();
    }

    public List<JsonDocument> SelectAsJson(IWhereClause? filter)
    {
        return Select(filter).Select(e => _jsonHelper.ConvertEntityToJson(e)).ToList();
    }

    public JsonDocument SelectAsJsonByKey(object key)
    {
        return SelectAsJson(WhereClause.Create().Eq(_table.KeyColumn.ColumnName, key)).Single();
    }

    public object InsertFromJson(JsonDocument? json)
    {
        // TODO: Implement this.
        throw new NotImplementedException();
    }
}
