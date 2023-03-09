namespace CrupestApi.Users.Entities;

public class Role
{
    public long Id { get; set; }

    public string Name { get; set; } = default!;

    public string? DisplayName { get; set; }

    public string? Description { get; set; }
}
