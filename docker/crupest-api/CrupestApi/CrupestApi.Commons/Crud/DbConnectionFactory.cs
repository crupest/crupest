using System.Data;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons.Crud;

public interface IDbConnectionFactory
{
    IDbConnection Get(string? name = null);
    bool ShouldDisposeConnection { get; }
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

    public bool ShouldDisposeConnection => true;
}

public class SqliteMemoryConnectionFactory : IDbConnectionFactory, IDisposable
{
    private readonly Dictionary<string, IDbConnection> _connections = new();

    public IDbConnection Get(string? name = null)
    {
        name = name ?? "crupest-api";

        if (_connections.TryGetValue(name, out var connection))
        {
            return connection;
        }
        else
        {
            var connectionString = new SqliteConnectionStringBuilder()
            {
                DataSource = ":memory:",
                Mode = SqliteOpenMode.ReadWriteCreate
            }.ToString();

            connection = new SqliteConnection(connectionString);
            _connections.Add(name, connection);
            return connection;
        }
    }

    public bool ShouldDisposeConnection => false;


    public void Dispose()
    {
        foreach (var connection in _connections.Values)
        {
            connection.Dispose();
        }
    }
}
