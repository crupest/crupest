using System.Security.Cryptography;
using System.Text;
using CrupestApi.Commons.Crud;

namespace CrupestApi.Commons.Secrets;

public class SecretInfo
{
    [Column(NotNull = true)]
    public string Key { get; set; } = default!;
    [Column(NotNull = true, NoUpdate = true, ActAsKey = true)]
    public string Secret { get; set; } = default!;
    [Column(DefaultEmptyForString = true)]
    public string Description { get; set; } = default!;
    [Column(NotNull = false)]
    public DateTime? ExpireTime { get; set; }
    [Column(NotNull = true)]
    public bool Revoked { get; set; }
    [Column(NotNull = true)]
    public DateTime CreateTime { get; set; }

    private static RandomNumberGenerator RandomNumberGenerator = RandomNumberGenerator.Create();

    private static string GenerateRandomKey(int length)
    {
        const string chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        var result = new StringBuilder(length);
        lock (RandomNumberGenerator)
        {
            for (int i = 0; i < length; i++)
            {
                result.Append(chars[RandomNumberGenerator.GetInt32(chars.Length)]);
            }
        }
        return result.ToString();
    }


    public static string SecretDefaultValueGenerator()
    {
        return GenerateRandomKey(16);
    }

    public static DateTime CreateTimeDefaultValueGenerator()
    {
        return DateTime.UtcNow;
    }
}
