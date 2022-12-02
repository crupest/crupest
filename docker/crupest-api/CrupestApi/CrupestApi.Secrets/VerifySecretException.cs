namespace CrupestApi.Secrets;

public class VerifySecretException : Exception
{
    public VerifySecretException(string requestKey, string message) : base(message)
    {
        RequestKey = requestKey;
    }

    public string RequestKey { get; set; }
}