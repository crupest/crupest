using CrupestApi.Commons;

namespace CrupestApi.Secrets;

public static class SecretsWebApplicationExtensions
{
    public static WebApplication UseCatchVerifySecretException(this WebApplication app)
    {
        app.Use(async (context, next) =>
        {
            try
            {
                await next(context);
            }
            catch (VerifySecretException e)
            {
                await context.Response.WriteErrorMessageAsync(e.Message, 401);
            }
        });

        return app;
    }

    public static async Task CheckSecret(this HttpContext context, string key)
    {
        var secretsService = context.RequestServices.GetRequiredService<ISecretsService>();
        await secretsService.VerifySecretForHttpRequestAsync(context.Request, SecretsConstants.SecretManagementKey);
    }

    public static WebApplication MapSecrets(this WebApplication app, string path)
    {
        app.MapGet(path, async (context) =>
        {
            await context.CheckSecret(SecretsConstants.SecretManagementKey);
            var secretsService = context.RequestServices.GetRequiredService<ISecretsService>();
            var secrets = secretsService.GetSecretListAsync();
            await context.Response.WriteJsonAsync(secrets);
        });

        return app;
    }
}
