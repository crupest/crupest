namespace CrupestApi.Secrets;

public class SecretCreateRequest
{
    public string Key { get; set; } = default!;
    public string Secret { get; set; } = default!;
    public string Description { get; set; } = default!;
    public DateTime? ExpireTime { get; set; }
}