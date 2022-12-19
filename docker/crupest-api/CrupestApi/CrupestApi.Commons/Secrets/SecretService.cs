using CrupestApi.Commons;
using CrupestApi.Commons.Crud;

namespace CrupestApi.Commons.Secrets;

public class SecretService : CrudService<SecretInfo>, ISecretService
{
    public SecretService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, EntityJsonHelper<SecretInfo> jsonHelper, ILoggerFactory loggerFactory)
        : base(tableInfoFactory, dbConnectionFactory, jsonHelper, loggerFactory)
    {

    }

    public List<string> GetPermissions(string secret)
    {
        var list = _table.Select<SecretInfo>(_dbConnection,
            where: WhereClause.Create().Eq(nameof(SecretInfo.Secret), secret));
        return list.Select(x => x.Key).ToList();
    }
}
