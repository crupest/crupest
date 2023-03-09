namespace CrupestApi.Users.Entities;

public class UserCredential
{
    public long Id { get; set; }

    public long UserId { get; set; }

    public string Password { get; set; } = default!;
}
