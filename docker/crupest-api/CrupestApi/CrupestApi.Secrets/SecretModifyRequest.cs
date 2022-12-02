namespace CrupestApi.Secrets;

public class SecretModifyRequest
{
    public SecretModifyRequest()
    {

    }

    public SecretModifyRequest(string? key, string? description)
    {
        Key = key;
        Description = description;
        SetExpireTime = false;
        ExpireTime = null;
    }

    public SecretModifyRequest(string? key, string? description, DateTime? expireTime)
    {
        Key = key;
        Description = description;
        SetExpireTime = true;
        ExpireTime = expireTime;
    }

    public string? Key { get; set; }
    public string? Description { get; set; }
    public bool SetExpireTime { get; set; }
    public DateTime? ExpireTime { get; set; }
}
