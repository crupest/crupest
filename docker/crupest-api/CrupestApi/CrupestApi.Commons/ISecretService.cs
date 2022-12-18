namespace CrupestApi.Commons;

interface ISecretService
{
    List<string> GetPermissions(string secret);
}
