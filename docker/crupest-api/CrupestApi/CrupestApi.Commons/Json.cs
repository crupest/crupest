using System.Text.Json;
using Microsoft.Extensions.Options;

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

    public static async Task WriteJsonAsync<T>(this HttpResponse response, T bodyObject, int statusCode, HttpResponseAction? beforeWriteBody, CancellationToken cancellationToken = default)
    {
        await response.WriteJsonAsync(bodyObject, statusCode, (context) =>
        {
            beforeWriteBody?.Invoke(context);
            return Task.CompletedTask;
        }, cancellationToken);
    }

    public static async Task WriteJsonAsync<T>(this HttpResponse response, T bodyObject, int statusCode = 200, AsyncHttpResponseAction? beforeWriteBody = null, CancellationToken cancellationToken = default)
    {
        var jsonOptions = response.HttpContext.RequestServices.GetRequiredService<IOptionsSnapshot<JsonSerializerOptions>>();
        byte[] json = JsonSerializer.SerializeToUtf8Bytes<T>(bodyObject, jsonOptions.Value);

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

    public static async Task WriteMessageAsync(this HttpResponse response, string message, int statusCode = 200, HttpResponseAction? beforeWriteBody = null, CancellationToken cancellationToken = default)
    {
        await response.WriteJsonAsync(new ErrorBody(message), statusCode: statusCode, beforeWriteBody, cancellationToken);
    }
}
