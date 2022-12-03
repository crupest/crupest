using System.Security.Cryptography;
using System.Text;
using CrupestApi.Commons;
using Dapper;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Options;

namespace CrupestApi.Secrets;

public class SecretsService : ISecretsService
{
    private readonly IOptionsSnapshot<CrupestApiConfig> _crupestApiConfig;
    private readonly ILogger<SecretsService> _logger;

    public SecretsService(IOptionsSnapshot<CrupestApiConfig> crupestApiConfig, ILogger<SecretsService> logger)
    {
        _crupestApiConfig = crupestApiConfig;
        _logger = logger;
    }

    private string GetDatabasePath()
    {
        return Path.Combine(_crupestApiConfig.Value.DataDir, "secrets.db");
    }

    private async Task<SqliteConnection> EnsureDatabase()
    {
        var dataSource = GetDatabasePath();
        var connectionStringBuilder = new SqliteConnectionStringBuilder()
        {
            DataSource = dataSource
        };

        if (!File.Exists(dataSource))
        {
            _logger.LogInformation("Data source {0} does not exist. Create one.", dataSource);
            connectionStringBuilder.Mode = SqliteOpenMode.ReadWriteCreate;
            var connectionString = connectionStringBuilder.ToString();
            var connection = new SqliteConnection(connectionString);
            var transaction = await connection.BeginTransactionAsync();

            connection.Execute(@"
CREATE TABLE secrets (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Key TEXT NOT NULL,
    Secret TEXT NOT NULL,
    Description TEXT NOT NULL,
    ExpireTime TEXT,
    Revoked INTEGER NOT NULL,
    CreateTime TEXT NOT NULL
);

CREATE INDEX secrets_key ON secrets (key);

INSERT INTO secrets (Key, Secret, Description, ExpireTime, Revoked, CreateTime) VALUES (@SecretManagementKey, 'crupest', 'This is the default secret management key.', NULL, 0, @CreateTime);
            ",
            new
            {
                SecretManagementKey = SecretsConstants.SecretManagementKey,
                CreateTime = DateTime.Now.ToString("O"),
            });

            await transaction.CommitAsync();

            _logger.LogInformation("{0} created with 'crupest' as the default secret management value. Please immediate revoke it and create a new one.", dataSource);
            return connection;
        }
        else
        {
            _logger.LogInformation("Data source {0} already exists. Will use it.");
            connectionStringBuilder.Mode = SqliteOpenMode.ReadWrite;
            var connectionString = connectionStringBuilder.ToString();
            return new SqliteConnection(connectionString);
        }
    }

    private string GenerateRandomKey(int length)
    {
        const string alphanum = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        using var randomNumberGenerator = RandomNumberGenerator.Create();
        var result = new StringBuilder(length);
        for (int i = 0; i < length; i++)
        {
            result.Append(alphanum[i]);
        }
        return result.ToString();
    }

    public async Task<SecretInfo> CreateSecretAsync(string key, string description, DateTime? expireTime = null)
    {
        var dbConnection = await EnsureDatabase();

        var secret = GenerateRandomKey(16);
        var now = DateTime.Now;

        dbConnection.Execute(@"
INSERT INTO secrets (Key, Secret, Description, ExpireTime, Revoked, CreateTime) VALUES (@Key, @Secret, @Description, @ExpireTime, 0, @CreateTime);
        ",
        new
        {
            Key = key,
            Secret = secret,
            Description = description,
            ExpireTime = expireTime?.ToString("O"),
            CreateTime = now.ToString("O"),
        });

        return new SecretInfo(key, secret, description, expireTime, false, now);
    }

    public async Task<List<SecretInfo>> GetSecretListAsync(bool includeExpired = false, bool includeRevoked = false)
    {
        var dbConnection = await EnsureDatabase();

        var query = await dbConnection.QueryAsync<SecretInfo>(@"
SELECT Key, Secret, Description, ExpireTime, Revoked, CreateTime FROM secrets
WHERE @IncludeExpired OR ExpireTime IS NULL OR ExpireTime > @Now AND
        @IncludeRevoked OR Revoked = 0;
        ", new
        {
            IncludeExpired = includeExpired,
            IncludeRevoked = includeRevoked,
            Now = DateTime.Now.ToString("O"),
        });

        return query.ToList();
    }

    public async Task<List<SecretInfo>> GetSecretListByKeyAsync(string key, bool includeExpired = false, bool includeRevoked = false)
    {
        var dbConnection = await EnsureDatabase();

        var query = await dbConnection.QueryAsync<SecretInfo>(@"
SELECT Key, Secret, Description, ExpireTime, Revoked, CreateTime FROM secrets
WHERE Key = @Key AND
(@IncludeExpired OR ExpireTime IS NULL OR ExpireTime > @Now) AND
(@IncludeRevoked OR Revoked = 0);
        ", new
        {
            Key = key,
            IncludeExpired = includeExpired,
            IncludeRevoked = includeRevoked,
            Now = DateTime.Now.ToString("O"),
        });

        return query.ToList();
    }

    public Task<SecretInfo> ModifySecretAsync(string secret, SecretModifyRequest modifyRequest)
    {
        throw new NotImplementedException();
    }

    public Task RevokeSecretAsync(string secret)
    {
        throw new NotImplementedException();
    }

    public Task<bool> VerifySecretAsync(string key, string secret)
    {
        throw new NotImplementedException();
    }

    public Task VerifySecretForHttpRequestAsync(HttpRequest request, string key, string queryKey = "secret")
    {
        throw new NotImplementedException();
    }
}
