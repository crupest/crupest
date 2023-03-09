namespace CrupestApi.Users.Entities;

public class UserMetadata
{
    public long Id { get; set; }
    
    public long UserId { get; set; }

    public string Key { get; set; } = default!;

    public string Value { get; set; } = default!;
}
