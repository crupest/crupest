using Dapper;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons.Crud;

public class CrudService<TEntity>
{
    protected readonly TableInfo _table;
    protected readonly IOptionsSnapshot<CrupestApiConfig> _crupestApiOptions;
    protected readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(IOptionsSnapshot<CrupestApiConfig> crupestApiOptions, ILogger<CrudService<TEntity>> logger)
    {
        _table = new TableInfo(typeof(TEntity));
        _crupestApiOptions = crupestApiOptions;
        _logger = logger;
    }

    public virtual string GetDbConnectionString()
    {
        var fileName = Path.Combine(_crupestApiOptions.Value.DataDir, "crupest-api.db");

        return new SqliteConnectionStringBuilder()
        {
            DataSource = fileName,
            Mode = SqliteOpenMode.ReadWriteCreate
        }.ToString();
    }


    public async Task<SqliteConnection> CreateDbConnection()
    {
        var connection = new SqliteConnection(GetDbConnectionString());
        await connection.OpenAsync();
        return connection;
    }

    public virtual async Task DoInitializeDatabase(SqliteConnection connection)
    {
        await using var transaction = await connection.BeginTransactionAsync();
        await connection.ExecuteAsync(_table.GenerateCreateTableSql(), transaction: transaction);
        await transaction.CommitAsync();
    }

    public virtual async Task<SqliteConnection> EnsureDatabase()
    {
        var connection = await CreateDbConnection();
        var exist = await _table.CheckExistence(connection);
        if (!exist)
        {
            await DoInitializeDatabase(connection);
        }
        return connection;
    }


    public virtual async Task<IEnumerable<TEntity>> QueryAsync(WhereClause? where = null, OrderByClause? orderBy = null, int? skip = null, int? limit = null)
    {
        var connection = await EnsureDatabase();
        DynamicParameters parameters;
        var sql = _table.GenerateSelectSql(where, orderBy, skip, limit, out parameters);
        return await connection.QueryAsync<TEntity>(sql, parameters);
    }
}
