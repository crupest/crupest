public interface IBasicUserService
{
    Task<bool> TokenHasPermissionAsync(string token, string permission);
}
