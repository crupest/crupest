using System.Data;
using CrupestApi.Commons.Crud;

namespace CrupestApi.Commons.Secrets;

public class SecretService : CrudService<SecretInfo>, ISecretService
{
    public SecretService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, EntityJsonHelper<SecretInfo> jsonHelper, ILoggerFactory loggerFactory)
        : base(tableInfoFactory, dbConnectionFactory, jsonHelper, loggerFactory)
    {

    }

    protected override void DoInitializeDatabase(IDbConnection connection)
    {
        base.DoInitializeDatabase(connection);
        using var transaction = connection.BeginTransaction();
        var insertClause = InsertClause.Create()
            .Add(nameof(SecretInfo.Key), SecretsConstants.SecretManagementKey)
            .Add(nameof(SecretInfo.Secret), "crupest")
            .Add(nameof(SecretInfo.Description), "This is the init key. Please revoke it immediately after creating a new one.");
        _table.Insert(connection, insertClause);
        transaction.Commit();
    }

    public void CreateTestSecret(string key, string secret)
    {
        var connection = _dbConnection;
        var insertClause = InsertClause.Create()
               .Add(nameof(SecretInfo.Key), key)
               .Add(nameof(SecretInfo.Secret), secret)
               .Add(nameof(SecretInfo.Description), "Test secret.");
        _table.Insert(connection, insertClause);
    }

    public List<string> GetPermissions(string secret)
    {
        var list = _table.Select<SecretInfo>(_dbConnection,
            where: WhereClause.Create().Eq(nameof(SecretInfo.Secret), secret));
        return list.Select(x => x.Key).ToList();
    }
}
