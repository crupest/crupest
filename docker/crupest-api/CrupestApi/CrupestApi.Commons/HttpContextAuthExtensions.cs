namespace CrupestApi.Commons;

public static class HttpContextAuthExtensions
{
    public static string? GetToken(this HttpRequest request)
    {
        var token = request.Headers["Authorization"].ToString();
        if (token.StartsWith("Bearer "))
        {
            token = token.Substring("Bearer ".Length);
            return token;
        }

        if (request.Query.TryGetValue("token", out var tokenValues))
        {
            return tokenValues.Last();
        }

        return null;
    }

    public static bool RequirePermission(this HttpContext context, string? permission)
    {
        if (permission is null) return true;

        var token = context.Request.GetToken();
        if (token is null)
        {
            context.ResponseMessageAsync("Unauthorized", 401);
            return false;
        }

        var secretService = context.RequestServices.GetRequiredService<ISecretService>();
        var permissions = secretService.GetPermissions(token);
        if (!permissions.Contains(permission))
        {
            context.ResponseMessageAsync("Forbidden", 403);
            return false;
        }
        return true;
    }
}
