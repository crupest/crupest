using Dapper;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons.Crud;

public class CrudService<TEntity>
{
    protected readonly TableInfo _table;
    protected readonly IOptionsSnapshot<CrupestApiConfig> _crupestApiOptions;
    private readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(ServiceProvider services)
    {
        _table = new TableInfo(typeof(TEntity));
        _crupestApiOptions = services.GetRequiredService<IOptionsSnapshot<CrupestApiConfig>>();
        _logger = services.GetRequiredService<ILogger<CrudService<TEntity>>>();
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

    public virtual async Task<int> InsertAsync(InsertClause insert)
    {
        var connection = await EnsureDatabase();
        DynamicParameters parameters;
        var sql = _table.GenerateInsertSql(insert, out parameters);
        return await connection.ExecuteAsync(sql, parameters);
    }

    public virtual async Task<int> UpdateAsync(WhereClause? where, UpdateClause update)
    {
        var connection = await EnsureDatabase();
        DynamicParameters parameters;
        var sql = _table.GenerateUpdateSql(where, update, out parameters);
        return await connection.ExecuteAsync(sql, parameters);
    }

    public virtual async Task<int> DeleteAsync(WhereClause? where)
    {
        var connection = await EnsureDatabase();
        DynamicParameters parameters;
        var sql = _table.GenerateDeleteSql(where, out parameters);
        return await connection.ExecuteAsync(sql, parameters);
    }
}
