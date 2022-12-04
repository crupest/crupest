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
                await context.Response.WriteErrorMessageAsync(e.Message, e.Kind == VerifySecretException.ErrorKind.Unauthorized ? 401 : 403);
            }
        });

        return app;
    }

    public static async Task CheckSecret(this HttpContext context, string? key)
    {
        var secretsService = context.RequestServices.GetRequiredService<ISecretsService>();
        await secretsService.VerifySecretForHttpRequestAsync(context.Request, key);
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

        app.MapGet(path + "/:secret", async (context) =>
        {
            await context.CheckSecret(SecretsConstants.SecretManagementKey);
            var secretsService = context.RequestServices.GetRequiredService<ISecretsService>();
            var secret = context.Request.RouteValues["secret"];
            if (secret is null)
            {
                await context.Response.WriteErrorMessageAsync("Secret path parameter is invalid.");
                return;
            }
            var secretInfo = secretsService.GetSecretAsync((string)secret);
            await context.Response.WriteJsonAsync(secretInfo);
        });

        app.MapPost(path, async (context) =>
        {
            await context.CheckSecret(SecretsConstants.SecretManagementKey);
            var secretsService = context.RequestServices.GetRequiredService<ISecretsService>();
            var request = await context.Request.ReadFromJsonAsync<SecretCreateRequest>();
            if (request is null)
            {
                await context.Response.WriteErrorMessageAsync("Failed to deserialize request body to SecretCreateRequest.");
                return;
            }
            var secret = await secretsService.CreateSecretAsync(request.Key, request.Description, request.ExpireTime);
            await context.Response.WriteJsonAsync(secret, 201, beforeWriteBody: (response) =>
            {
                response.Headers.Location = context.Request.Path + "/" + secret.Secret;
            });
        });

        app.MapPost(path + "/:secret/revoke", async (context) =>
        {
            await context.CheckSecret(SecretsConstants.SecretManagementKey);
            var secretsService = context.RequestServices.GetRequiredService<ISecretsService>();
            var secret = context.Request.RouteValues["secret"];
            if (secret is null)
            {
                await context.Response.WriteErrorMessageAsync("Secret path parameter is invalid.");
                return;
            }

            try
            {
                await secretsService.RevokeSecretAsync((string)secret);
                await context.Response.WriteMessageAsync("Secret revoked.");
            }
            catch (EntityNotExistException)
            {
                await context.Response.WriteErrorMessageAsync("Secret to revoke is invalid.");
            }
        });

        return app;
    }
}
