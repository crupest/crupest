using System.Diagnostics;
using CrupestApi.Commons;
using CrupestApi.Commons.Crud;
using Dapper;

namespace CrupestApi.Secrets;

public class SecretsService : CrudService<SecretInfo>
{
    private readonly ILogger<SecretsService> _logger;

    public SecretsService(ITableInfoFactory tableInfoFactory, IDbConnectionFactory dbConnectionFactory, ILoggerFactory loggerFactory)
    : base("secrets", tableInfoFactory, dbConnectionFactory, loggerFactory)
    {
        _logger = loggerFactory.CreateLogger<SecretsService>();
    }
}
