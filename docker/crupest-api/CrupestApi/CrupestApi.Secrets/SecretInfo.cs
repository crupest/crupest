using CrupestApi.Commons.Crud;

namespace CrupestApi.Secrets;

public class SecretInfo
{
    [Column(NotNull = true)]
    public string Key { get; set; } = default!;
    [Column(NotNull = true)]
    public string Secret { get; set; } = default!;
    [Column(DefaultEmptyForString = true)]
    public string Description { get; set; } = default!;
    [Column(NotNull = false)]
    public DateTime ExpireTime { get; set; }
    public bool Revoked { get; set; }
    public DateTime CreateTime { get; set; }
}
