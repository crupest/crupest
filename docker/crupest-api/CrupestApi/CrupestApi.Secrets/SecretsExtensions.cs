using CrupestApi.Commons.Secrets;
using CrupestApi.Commons.Crud;

namespace CrupestApi.Secrets;

public static class SecretsExtensions
{
    public static IServiceCollection AddSecrets(this IServiceCollection services)
    {
        services.AddCrud<SecretInfo, SecretService>();
        return services;
    }

    public static WebApplication MapSecrets(this WebApplication webApplication, string path = "/api/secrets")
    {
        webApplication.MapCrud<SecretInfo>(path, SecretsConstants.SecretManagementKey);
        return webApplication;
    }
}
