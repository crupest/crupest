using CrupestApi.Commons.Crud;

namespace CrupestApi.Secrets;

public class SecretInfo
{
    [Column(NotNull = true)]
    public string Key { get; set; } = default!;
    [Column(NotNull = true, ClientGenerate = true)]
    public string Secret { get; set; } = default!;
    [Column(DefaultEmptyForString = true)]
    public string Description { get; set; } = default!;
    [Column(NotNull = false)]
    public DateTime? ExpireTime { get; set; }
    [Column(NotNull = true)]
    public bool Revoked { get; set; }
    [Column(NotNull = true)]
    public DateTime CreateTime { get; set; }
}
