using System.Data;
using CrupestApi.Commons.Crud;
using CrupestApi.Commons.Crud.Migrations;

namespace CrupestApi.Commons.Secrets;

public class SecretService : CrudService<SecretInfo>, ISecretService
{
    private readonly ILogger<SecretService> _logger;

    public SecretService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, IDatabaseMigrator migrator, ILoggerFactory loggerFactory)
        : base(tableInfoFactory, dbConnectionFactory, migrator, loggerFactory)
    {
        _logger = loggerFactory.CreateLogger<SecretService>();
    }

    protected override void AfterMigrate(IDbConnection connection, TableInfo table, ILoggerFactory loggerFactory)
    {
        if (table.SelectCount(connection) == 0)
        {
            loggerFactory.CreateLogger<SecretService>().LogInformation("No secrets found, insert default secrets.");
            using var transaction = connection.BeginTransaction();
            var insertClause = InsertClause.Create()
                .Add(nameof(SecretInfo.Key), SecretsConstants.SecretManagementKey)
                .Add(nameof(SecretInfo.Secret), "crupest")
                .Add(nameof(SecretInfo.Description), "This is the init key. Please revoke it immediately after creating a new one.");
            _table.Insert(connection, insertClause, out var _);
            transaction.Commit();
        }
    }

    public void CreateTestSecret(string key, string secret)
    {
        var connection = _dbConnection;
        var insertClause = InsertClause.Create()
               .Add(nameof(SecretInfo.Key), key)
               .Add(nameof(SecretInfo.Secret), secret)
               .Add(nameof(SecretInfo.Description), "Test secret.");
        _table.Insert(connection, insertClause, out var _);
    }

    public List<string> GetPermissions(string secret)
    {
        var list = _table.Select<SecretInfo>(_dbConnection,
            where: WhereClause.Create().Eq(nameof(SecretInfo.Secret), secret));
        return list.Select(x => x.Key).ToList();
    }
}
