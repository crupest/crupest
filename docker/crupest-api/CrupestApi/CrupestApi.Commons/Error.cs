namespace CrupestApi.Commons;

public class ErrorBody
{
    public ErrorBody(string message)
    {
        Message = message;
    }

    public string Message { get; set; }
}

public static class CrupestApiErrorExtensions
{
    public static async Task WriteErrorMessageAsync(this HttpResponse response, string message, int statusCode = 400, HttpResponseAction? beforeWriteBody = null, CancellationToken cancellationToken = default)
    {
        await response.WriteJsonAsync(new ErrorBody(message), statusCode: statusCode, beforeWriteBody, cancellationToken);
    }
}
