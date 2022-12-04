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

    public SecretModifyRequest(string? key, string? description, DateTime? expireTime, bool revoked)
    {
        if (revoked is not true)
        {
            throw new ArgumentException("Revoked can only be set to true.");
        }

        Key = key;
        Description = description;
        SetExpireTime = true;
        ExpireTime = expireTime;
        Revoked = revoked;
    }

    public string? Key { get; set; }
    public string? Description { get; set; }
    public bool SetExpireTime { get; set; }
    public DateTime? ExpireTime { get; set; }
    public bool Revoked { get; set; }
}
