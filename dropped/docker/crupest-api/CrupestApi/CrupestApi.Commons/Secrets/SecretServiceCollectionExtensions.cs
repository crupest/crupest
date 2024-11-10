using Microsoft.Extensions.DependencyInjection.Extensions;

namespace CrupestApi.Commons.Secrets;

public static class SecretServiceCollectionExtensions
{
    public static IServiceCollection AddSecrets(this IServiceCollection services)
    {
        services.TryAddScoped<ISecretService, SecretService>();
        return services;
    }
}
