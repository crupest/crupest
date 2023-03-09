namespace CrupestApi.Users.Entities;

public class RolePermission
{
    public long Id { get; set; }

    public long RoleId { get; set; }

    public long PermissionId { get; set; }
}
