using System.Data;
using Dapper;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons.Crud;

public class CrudService<TEntity>
{
    protected readonly IOptionsSnapshot<CrupestApiConfig> _crupestApiOptions;
    protected readonly ILogger<CrudService<TEntity>> _logger;

    public CrudService(IOptionsSnapshot<CrupestApiConfig> crupestApiOptions, ILogger<CrudService<TEntity>> logger)
    {
        _crupestApiOptions = crupestApiOptions;
        _logger = logger;
    }

    public virtual string GetTableName()
    {
        return typeof(TEntity).Name;
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

    public virtual async Task<bool> CheckDatabaseExist(SqliteConnection connection)
    {
        var tableName = GetTableName();
        var count = (await connection.QueryAsync<int>(
            @"SELECT count(*) FROM sqlite_schema WHERE type = 'table' AND tbl_name = @TableName;",
            new { TableName = tableName })).Single();
        if (count == 0)
        {
            return false;
        }
        else if (count > 1)
        {
            throw new DatabaseInternalException($"More than 1 table has name {tableName}. What happened?");
        }
        else
        {
            return true;
        }
    }

    public string GetDatabaseTypeName(Type type)
    {
        if (type == typeof(int))
        {
            return "INTEGER";
        }
        else if (type == typeof(double))
        {
            return "REAL";
        }
        else if (type == typeof(bool))
        {
            return "BOOLEAN";
        }
        else
        {
            throw new DatabaseInternalException($"Type {type} is not supported.");
        }
    }

    public string GetCreateTableColumnSql()
    {
        var properties = typeof(TEntity).GetProperties();
        var sql = string.Join(", ", properties.Select(p => $"{p.Name} {GetDatabaseTypeName(p.PropertyType)}"));
        return sql;
    }

    public virtual async Task DoInitializeDatabase(SqliteConnection connection)
    {
        await using var transaction = await connection.BeginTransactionAsync();
        var tableName = GetTableName();
        var columnSql = GetCreateTableColumnSql();
        var sql = $@"
CREATE TABLE {tableName}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    {columnSql}
);
        ";
        await connection.ExecuteAsync(sql, transaction: transaction);
        await transaction.CommitAsync();
    }

    public virtual async Task<SqliteConnection> EnsureDatabase()
    {
        var connection = await CreateDbConnection();
        var exist = await CheckDatabaseExist(connection);
        if (!exist)
        {
            await DoInitializeDatabase(connection);
        }
        return connection;
    }
}
