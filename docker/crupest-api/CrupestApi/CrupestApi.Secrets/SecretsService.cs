using System.Data;
using System.Diagnostics;
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

    private async Task<SecretInfo> GetSecretAsync(IDbConnection dbConnection, string secret)
    {
        var result = await dbConnection.QueryFirstOrDefaultAsync<SecretInfo>(@"
SELECT Id, Key, Secret, Description, ExpireTime, Revoked, CreateTime FROM secrets WHERE Secret = @Secret;
        ", new
        {
            Secret = secret
        });

        return result;

    }

    public async Task<SecretInfo?> GetSecretAsync(string secret)
    {
        using var dbConnection = await EnsureDatabase();
        return await GetSecretAsync(dbConnection, secret);
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

    public async Task<SecretInfo> ModifySecretAsync(string secret, SecretModifyRequest modifyRequest)
    {
        var dbConnection = await EnsureDatabase();

        var secretInfo = await GetSecretAsync(dbConnection, secret);

        if (secretInfo is null)
        {
            throw new EntityNotExistException("Secret not found.");
        }

        var queryParams = new DynamicParameters();
        var updateColumnList = new List<string>();

        if (modifyRequest.Key is not null)
        {
            queryParams.Add("Key", modifyRequest.Key);
            updateColumnList.Add("Key");
        }

        if (modifyRequest.Description is not null)
        {
            queryParams.Add("Description", modifyRequest.Description);
            updateColumnList.Add("Description");
        }

        if (modifyRequest.SetExpireTime is true)
        {
            queryParams.Add("ExpireTime", modifyRequest.ExpireTime?.ToString("O"));
            updateColumnList.Add("ExpireTime");
        }

        if (modifyRequest.Revoked is true && secretInfo.Revoked is not true)
        {
            queryParams.Add("Revoked", true);
            updateColumnList.Add("Revoked");
        }

        if (updateColumnList.Count == 0)
        {
            return secretInfo;
        }

        queryParams.Add("Secret", secret);

        var updateColumnString = updateColumnList.GenerateUpdateColumnString();

        var changeCount = await dbConnection.ExecuteAsync($@"
UPDATE secrets SET {updateColumnString} WHERE Secret = @Secret;
        ", queryParams);

        Debug.Assert(changeCount == 1);

        return secretInfo;
    }

    public async Task RevokeSecretAsync(string secret)
    {
        await ModifySecretAsync(secret, new SecretModifyRequest
        {
            Revoked = true,
        });
    }

    public async Task VerifySecretAsync(string? key, string? secret)
    {
        var dbConnection = await EnsureDatabase();

        if (secret is null)
        {
            if (key is not null)
            {
                throw new VerifySecretException(key, "A secret with given key is needed.");
            }
        }

        var entity = await dbConnection.QueryFirstOrDefaultAsync<SecretInfo>(@"
SELECT Id, Key, Secret, Description, ExpireTime, Revoked, CreateTime FROM secrets WHERE Key = @Key AND Secret = @Secret
        ", new
        {
            Key = key,
            Secret = secret,
        });

        if (entity is null)
        {
            throw new VerifySecretException(key, "Secret token is invalid.");
        }

        if (entity.Revoked is true)
        {
            throw new VerifySecretException(key, "Secret token is revoked.");
        }

        if (entity.ExpireTime is not null && DateTime.ParseExact(entity.ExpireTime, "O", null) > DateTime.Now)
        {
            throw new VerifySecretException(key, "Secret token is expired.");
        }

        if (key is not null)
        {
            if (entity.Key != key)
            {
                throw new VerifySecretException(key, "Secret is not for this key", VerifySecretException.ErrorKind.Forbidden);
            }
        }
    }

    public async Task VerifySecretForHttpRequestAsync(HttpRequest request, string? key, string queryKey = "secret")
    {
        string? secret = null;

        var authorizationHeaders = request.Headers.Authorization.ToList();
        if (authorizationHeaders.Count > 1)
        {
            _logger.LogWarning("There are multiple Authorization headers in the request. Will use the last one.");
        }
        if (authorizationHeaders.Count > 0)
        {
            var authorizationHeader = authorizationHeaders[^1] ?? "";
            if (!authorizationHeader.StartsWith("Bearer "))
            {
                throw new VerifySecretException(key, "Authorization header must start with 'Bearer '.");
            }

            secret = authorizationHeader.Substring("Bearer ".Length).Trim();
        }

        var secretQueryParam = request.Query[queryKey].ToList();
        if (secretQueryParam.Count > 1)
        {
            _logger.LogWarning($"There are multiple '{queryKey}' query parameters in the request. Will use the last one.");
        }
        if (secretQueryParam.Count > 0)
        {
            if (secret is not null)
            {
                _logger.LogWarning("Secret found both in Authorization header and query parameter. Will use the one in query parameter.");
            }
            secret = secretQueryParam[^1] ?? "";
        }

        await VerifySecretAsync(key, secret);
    }
}
