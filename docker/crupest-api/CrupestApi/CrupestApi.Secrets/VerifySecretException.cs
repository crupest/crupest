namespace CrupestApi.Secrets;

public class VerifySecretException : Exception
{
    public VerifySecretException(string? requestKey, string message, ErrorKind kind = ErrorKind.Unauthorized) : base(message)
    {
        RequestKey = requestKey;
        Kind = kind;
    }

    public enum ErrorKind
    {
        Unauthorized,
        Forbidden
    }

    public ErrorKind Kind { get; set; }

    public string? RequestKey { get; set; }
}
