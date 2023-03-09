namespace CrupestApi.Users.Entities;

public class UserPermission
{
    public long Id { get; set; }

    public long UserId { get; set; }

    public long PermissionId { get; set; }
}
