namespace CrupestApi.Secrets;

public class SecretInfo
{
    public SecretInfo(string key, string secret, string description, DateTime? expireTime, bool revoked, DateTime createdTime)
    {
        Key = key;
        Secret = secret;
        Description = description;
        ExpireTime = expireTime;
        Revoked = revoked;
        CreateTime = createdTime;
    }

    public string Key { get; set; }
    public string Secret { get; set; }
    public string Description { get; set; }
    public DateTime? ExpireTime { get; set; }
    public bool Revoked { get; set; }
    public DateTime CreateTime { get; set; }
}
