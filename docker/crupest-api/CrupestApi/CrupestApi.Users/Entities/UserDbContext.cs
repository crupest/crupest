using Microsoft.EntityFrameworkCore;

namespace CrupestApi.Users.Entities;

public class UserDbContext : DbContext
{
    DbSet<User> Users { get; set; } = default!;
    DbSet<UserCredential> UserCredentials { get; set; } = default!;
    DbSet<UserMetadata> UserMetadata { get; set; } = default!;

    DbSet<Permission> Permissions { get; set; } = default!;
    DbSet<Role> Roles { get; set; } = default!;
    DbSet<RolePermission> RolePermissions { get; set; } = default!;
    DbSet<UserPermission> UserPermissions { get; set; } = default!;
    DbSet<UserRole> UserRoles { get; set; } = default!;
}
