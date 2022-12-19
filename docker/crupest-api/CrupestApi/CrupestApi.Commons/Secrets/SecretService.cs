using CrupestApi.Commons.Crud;

namespace CrupestApi.Commons.Secrets;

public class SecretService : CrudService<SecretInfo>, ISecretService
{
    public SecretService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, EntityJsonHelper<SecretInfo> jsonHelper, ILoggerFactory loggerFactory)
        : base(tableInfoFactory, dbConnectionFactory, jsonHelper, loggerFactory)
    {

    }

    protected override void DoInitializeDatabase(System.Data.IDbConnection connection)
    {
        base.DoInitializeDatabase(connection);
        using var transaction = connection.BeginTransaction();
        _table.Insert(connection, new SecretInfo
        {
            Key = SecretsConstants.SecretManagementKey,
            Secret = "crupest",
            Description = "This is the init key. Please revoke it immediately after creating a new one."
        });
        transaction.Commit();
    }

    public List<string> GetPermissions(string secret)
    {
        var list = _table.Select<SecretInfo>(_dbConnection,
            where: WhereClause.Create().Eq(nameof(SecretInfo.Secret), secret));
        return list.Select(x => x.Key).ToList();
    }
}
