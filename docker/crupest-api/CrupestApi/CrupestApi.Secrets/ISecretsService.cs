namespace CrupestApi.Secrets;

public interface ISecretsService
{
    Task<List<SecretInfo>> GetSecretListAsync(bool includeExpired = false, bool includeRevoked = false);

    Task<List<SecretInfo>> GetSecretListByKeyAsync(string key, bool includeExpired = false, bool includeRevoked = false);

    Task<bool> VerifySecretAsync(string key, string secret);

    // Check if "secret" query param exists and is only one. Then check the secret is valid for given key.
    // If check fails, will throw a VerifySecretException with proper message that can be send to client.
    Task VerifySecretForHttpRequestAsync(HttpRequest request, string key, string queryKey = "secret");

    Task<SecretInfo> CreateSecretAsync(string key, string description, DateTime? expireTime = null);

    Task RevokeSecretAsync(string secret);

    // Throw SecretNotExistException if request secret does not exist.
    Task<SecretInfo> ModifySecretAsync(string secret, SecretModifyRequest modifyRequest);
}
