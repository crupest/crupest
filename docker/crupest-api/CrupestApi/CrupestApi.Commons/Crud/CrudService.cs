using System.Data;
using Dapper;

namespace CrupestApi.Commons.Crud;

public class CrudService<TEntity> : IDisposable where TEntity : class
{
    protected readonly TableInfo _table;
    protected readonly string? _connectionName;
    protected readonly IDbConnection _dbConnection;
    private readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(string? connectionName, ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, ILoggerFactory loggerFactory)
    {
        _connectionName = connectionName;
        _table = tableInfoFactory.Get(typeof(TEntity));
        _dbConnection = dbConnectionFactory.Get(_connectionName);
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
        return _table.Select(_dbConnection, filter).Cast<TEntity>().ToList();
    }

    public int Insert(IInsertClause insertClause)
    {
        return _table.Insert(_dbConnection, insertClause);
    }

    public int Insert(TEntity entity)
    {
        return _table.Insert(_dbConnection, _table.GenerateInsertClauseFromEntity(entity));
    }

    public int Update(IUpdateClause updateClause, IWhereClause? filter)
    {
        return _table.Update(_dbConnection, filter, updateClause);
    }

    public int Delete(IWhereClause? filter)
    {
        return _table.Delete(_dbConnection, filter);
    }
}
