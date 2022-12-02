namespace CrupestApi.Secrets;

public class SecretNotExistException : Exception
{
    public SecretNotExistException(string requestSecret)
        : base($"Request secret {requestSecret} not found.")
    {
        RequestSecret = requestSecret;
    }

    public SecretNotExistException(string requestSecret, string message)
        : base(message)
    {
        RequestSecret = requestSecret;
    }

    public string RequestSecret { get; set; }
}