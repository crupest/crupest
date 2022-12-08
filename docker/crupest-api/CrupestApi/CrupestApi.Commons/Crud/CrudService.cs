using System.Data;
using Dapper;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons.Crud;

// TODO: Implement and register this service.
public class CrudService<TEntity> : IDisposable
{
    protected readonly TableInfo _table;
    protected readonly IDbConnection _dbConnection;
    protected readonly IOptionsSnapshot<CrupestApiConfig> _crupestApiOptions;
    private readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, IOptionsSnapshot<CrupestApiConfig> crupestApiOptions, ILogger<CrudService<TEntity>> logger)
    {
        _table = tableInfoFactory.Get(typeof(TEntity));
        _dbConnection = dbConnectionFactory.Get();
        _crupestApiOptions = crupestApiOptions;
        _logger = logger;

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
}
