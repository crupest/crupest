namespace CrupestApi.Commons;

public interface ISecretService
{
    List<string> GetPermissions(string secret);
}
