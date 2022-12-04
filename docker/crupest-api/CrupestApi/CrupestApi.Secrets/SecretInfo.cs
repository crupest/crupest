namespace CrupestApi.Secrets;

public class SecretInfo
{
    public SecretInfo(string key, string secret, string description, DateTime? expireTime, bool revoked, DateTime createdTime)
    {
        Key = key;
        Secret = secret;
        Description = description;
        ExpireTime = expireTime?.ToString("O");
        Revoked = revoked;
        CreateTime = createdTime.ToString("O");
    }

    public string Key { get; set; }
    public string Secret { get; set; }
    public string Description { get; set; }
    public string? ExpireTime { get; set; }
    public bool Revoked { get; set; }
    public string CreateTime { get; set; }
}
