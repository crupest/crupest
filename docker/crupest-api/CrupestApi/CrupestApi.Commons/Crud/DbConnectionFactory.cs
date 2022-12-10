using System.Data;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons.Crud;

public interface IDbConnectionFactory
{
    IDbConnection Get(string? name = null);
}

public class SqliteConnectionFactory : IDbConnectionFactory
{
    private readonly IOptionsMonitor<CrupestApiConfig> _apiConfigMonitor;

    public SqliteConnectionFactory(IOptionsMonitor<CrupestApiConfig> apiConfigMonitor)
    {
        _apiConfigMonitor = apiConfigMonitor;
    }

    public IDbConnection Get(string? name = null)
    {
        var connectionString = new SqliteConnectionStringBuilder()
        {
            DataSource = Path.Combine(_apiConfigMonitor.CurrentValue.DataDir, $"{name ?? "crupest-api"}.db"),
            Mode = SqliteOpenMode.ReadWriteCreate
        }.ToString();

        return new SqliteConnection(connectionString);
    }
}
