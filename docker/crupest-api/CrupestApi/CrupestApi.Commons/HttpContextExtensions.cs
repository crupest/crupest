using System.Text.Json;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons;

public delegate void HttpResponseAction(HttpResponse response);

public class MessageBody
{
    public MessageBody(string message)
    {
        Message = message;
    }

    public string Message { get; set; }
}

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

    public static async Task<JsonDocument> ReadJsonAsync(this HttpRequest request)
    {
        var jsonOptions = request.HttpContext.RequestServices.GetRequiredService<IOptionsSnapshot<JsonSerializerOptions>>();
        using var stream = request.Body;
        var body = await JsonSerializer.DeserializeAsync<JsonDocument>(stream, jsonOptions.Value);
        return body!;
    }

    public static async Task WriteJsonAsync<T>(this HttpResponse response, T bodyObject, int statusCode = 200, HttpResponseAction? beforeWriteBody = null, CancellationToken cancellationToken = default)
    {
        var jsonOptions = response.HttpContext.RequestServices.GetRequiredService<IOptionsSnapshot<JsonSerializerOptions>>();
        byte[] json = JsonSerializer.SerializeToUtf8Bytes<T>(bodyObject, jsonOptions.Value);

        var byteCount = json.Length;

        response.StatusCode = statusCode;
        response.Headers.ContentType = "application/json; charset=utf-8";
        response.Headers.ContentLength = byteCount;

        if (beforeWriteBody is not null)
        {
            beforeWriteBody(response);
        }

        await response.Body.WriteAsync(json, cancellationToken);
    }

    public static async Task WriteMessageAsync(this HttpResponse response, string message, int statusCode = 400, HttpResponseAction? beforeWriteBody = null, CancellationToken cancellationToken = default)
    {
        await response.WriteJsonAsync(new MessageBody(message), statusCode: statusCode, beforeWriteBody, cancellationToken);
    }
}
