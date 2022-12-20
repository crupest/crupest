namespace CrupestApi.Commons.Secrets;

public interface ISecretService
{
    void CreateTestSecret(string key, string secret);

    List<string> GetPermissions(string secret);
}
