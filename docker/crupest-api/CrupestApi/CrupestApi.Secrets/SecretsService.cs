using CrupestApi.Commons.Crud;

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
