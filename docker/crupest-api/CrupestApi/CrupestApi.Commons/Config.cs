namespace CrupestApi.Commons;

public class CrupestApiConfig
{
    public string DataDir { get; set; } = string.Empty;
}

public static class CrupestApiConfigExtensions
{
    public static IServiceCollection AddCrupestApiConfig(this IServiceCollection services)
    {
        services.AddOptions<CrupestApiConfig>().BindConfiguration("CrupestApi");
        services.PostConfigure<CrupestApiConfig>(config =>
        {
            if (string.IsNullOrEmpty(config.DataDir))
            {
                config.DataDir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    "crupest-api"
                );
            }
        });

        return services;
    }
}
