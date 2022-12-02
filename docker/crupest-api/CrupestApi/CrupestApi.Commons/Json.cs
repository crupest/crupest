using System.Text;
using System.Text.Json;

namespace CrupestApi.Commons;


public static class CrupestApiJsonExtensions
{
    public static IServiceCollection AddJsonOptions(this IServiceCollection services)
    {
        services.AddOptions<JsonSerializerOptions>();
        services.Configure<JsonSerializerOptions>(config =>
        {
            config.AllowTrailingCommas = true;
            config.PropertyNameCaseInsensitive = true;
            config.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
        });

        return services;
    }


    public static async Task WriteJsonAsync<T>(this HttpResponse response, T bodyObject, int statusCode = 200, HttpResponseAction? beforeWriteBody = null, CancellationToken cancellationToken = default)
    {
        var jsonOptions = response.HttpContext.RequestServices.GetRequiredService<JsonSerializerOptions>();
        byte[] json = JsonSerializer.SerializeToUtf8Bytes<T>(bodyObject, jsonOptions);

        var byteCount = json.Length;
        response.StatusCode = statusCode;
        response.Headers.ContentType = "application/json; charset=utf-8";
        response.Headers.ContentLength = byteCount;

        if (beforeWriteBody is not null)
        {
            await beforeWriteBody(response);
        }

        await response.Body.WriteAsync(json, cancellationToken);
    }
}
