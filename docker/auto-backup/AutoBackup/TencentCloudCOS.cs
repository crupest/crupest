using System.Net;
using System.Security.Cryptography;
using System.Text;


public static class TencentCloudCOSHelper
{
    public class Credentials
    {
        public Credentials(string secretId, string secretKey)
        {
            SecretId = secretId;
            SecretKey = secretKey;
        }

        public string SecretId { get; }
        public string SecretKey { get; }
    }

    public class RequestInfo
    {
        public RequestInfo(string method, string urlPathname, IEnumerable<KeyValuePair<string, string>> parameters, IEnumerable<KeyValuePair<string, string>> headers)
        {
            Method = method;
            UrlPathname = urlPathname;
            Parameters = new Dictionary<string, string>(parameters);
            Headers = new Dictionary<string, string>(headers);
        }

        public string Method { get; }
        public string UrlPathname { get; }
        public IReadOnlyDictionary<string, string> Parameters { get; }
        public IReadOnlyDictionary<string, string> Headers { get; }
    }

    public class TimeDuration
    {
        public TimeDuration(DateTimeOffset start, DateTimeOffset end)
        {
            if (start > end)
            {
                throw new ArgumentException("Start time must be earlier than end time.");
            }

            Start = start;
            End = end;
        }

        public DateTimeOffset Start { get; }
        public DateTimeOffset End { get; }
    }

    public static string GenerateSign(Credentials credentials, RequestInfo request, TimeDuration signValidTime)
    {
        List<(string key, string value)> Transform(IEnumerable<KeyValuePair<string, string>> raw)
        {
            if (raw == null)
                return new List<(string key, string value)>();

            var sorted = raw.Select(p => (key: WebUtility.UrlEncode(p.Key.ToLower()), value: WebUtility.UrlEncode(p.Value))).ToList();
            sorted.Sort((left, right) => string.CompareOrdinal(left.key, right.key));
            return sorted;
        }

        var transformedParameters = Transform(request.Parameters);
        var transformedHeaders = Transform(request.Headers);


        const string signAlgorithm = "sha1";

        static string ByteArrayToString(byte[] bytes)
        {
            return BitConverter.ToString(bytes).Replace("-", "").ToLower();
        }

        var keyTime = $"{signValidTime.Start.ToUnixTimeSeconds().ToString()};{signValidTime.End.ToUnixTimeSeconds().ToString()}";
        using HMACSHA1 hmac = new HMACSHA1(Encoding.ASCII.GetBytes(credentials.SecretKey));
        var signKey = ByteArrayToString(hmac.ComputeHash(Encoding.UTF8.GetBytes(keyTime)));

        static string Join(IEnumerable<(string key, string value)> raw)
        {
            return string.Join('&', raw.Select(p => string.Concat(p.key, "=", p.value)));
        }

        var httpParameters = Join(transformedParameters);
        var urlParamList = string.Join(';', transformedParameters.Select(p => p.key));
        var httpHeaders = Join(transformedHeaders);
        var headerList = string.Join(';', transformedHeaders.Select(h => h.key));

        var httpString = new StringBuilder()
            .Append(request.Method.ToLower()).Append('\n')
            .Append(request.UrlPathname).Append('\n')
            .Append(httpParameters).Append('\n')
            .Append(httpHeaders).Append('\n')
            .ToString();

        using var sha1 = SHA1.Create();
        string Sha1(string data)
        {
            var result = sha1.ComputeHash(Encoding.UTF8.GetBytes(data));
            return ByteArrayToString(result);
        }

        var stringToSign = new StringBuilder()
            .Append(signAlgorithm).Append('\n')
            .Append(keyTime).Append('\n')
            .Append(Sha1(httpString)).Append('\n')
            .ToString();

        hmac.Key = Encoding.UTF8.GetBytes(signKey);
        var signature = ByteArrayToString(hmac.ComputeHash(
            Encoding.UTF8.GetBytes(stringToSign)));


        List<(string, string)> result = new List<(string, string)>();
        result.Add(("q-sign-algorithm", signAlgorithm));
        result.Add(("q-ak", credentials.SecretId));
        result.Add(("q-sign-time", keyTime));
        result.Add(("q-key-time", keyTime));
        result.Add(("q-header-list", headerList));
        result.Add(("q-url-param-list", urlParamList));
        result.Add(("q-signature", signature));
        return Join(result);
    }

    private static string GetHost(string bucket, string region)
    {
        return $"{bucket}.cos.{region}.myqcloud.com";
    }

    public static async Task<bool> IsObjectExists(Credentials credentials, string region, string bucket, string key)
    {
        var host = GetHost(bucket, region);
        var encodedKey = WebUtility.UrlEncode(key);

        using var request = new HttpRequestMessage();
        request.Method = HttpMethod.Head;
        request.RequestUri = new Uri($"https://{host}/{encodedKey}");
        request.Headers.Host = host;
        request.Headers.Date = DateTimeOffset.Now;
        request.Headers.TryAddWithoutValidation("Authorization", GenerateSign(credentials, new RequestInfo(
            "head", "/" + key, new Dictionary<string, string>(),
            new Dictionary<string, string>
            {
                ["Host"] = host
            }
        ), new TimeDuration(DateTimeOffset.Now, DateTimeOffset.Now.AddMinutes(5))));

        using var client = new HttpClient();
        using var response = await client.SendAsync(request);

        if (response.IsSuccessStatusCode)
            return true;
        if (response.StatusCode == HttpStatusCode.NotFound)
            return false;

        throw new Exception($"Unknown response code. {response.ToString()}");
    }

    public static async Task PutObject(Credentials credentials, string region, string bucket, string key, Stream dataStream)
    {
        if (!dataStream.CanSeek)
        {
            throw new ArgumentException("Data stream must be seekable.");
        }

        if (dataStream.Seek(0, SeekOrigin.End) > 5L * 1024L * 1024L * 1024L)
        {
            throw new ArgumentException("Data stream must be smaller than 5GB.");
        }

        dataStream.Seek(0, SeekOrigin.Begin);

        var host = GetHost(bucket, region);
        var encodedKey = WebUtility.UrlEncode(key);
        using var md5Handler = MD5.Create();
        var md5 = Convert.ToBase64String(await md5Handler.ComputeHashAsync(dataStream));

        dataStream.Seek(0, SeekOrigin.Begin);

        const string kContentMD5HeaderName = "Content-MD5";

        using var httpRequest = new HttpRequestMessage()
        {
            Method = HttpMethod.Put,
            RequestUri = new Uri($"https://{host}/{encodedKey}")
        };
        httpRequest.Headers.Host = host;
        httpRequest.Headers.Date = DateTimeOffset.Now;

        using var httpContent = new StreamContent(dataStream);
        httpContent.Headers.Add(kContentMD5HeaderName, md5);
        httpRequest.Content = httpContent;

        var signedHeaders = new Dictionary<string, string>
        {
            ["Host"] = host,
            [kContentMD5HeaderName] = md5
        };

        httpRequest.Headers.TryAddWithoutValidation("Authorization", GenerateSign(credentials, new RequestInfo(
            "put", "/" + key, new Dictionary<string, string>(), signedHeaders
        ), new TimeDuration(DateTimeOffset.Now, DateTimeOffset.Now.AddMinutes(10))));

        using var client = new HttpClient();
        using var response = await client.SendAsync(httpRequest);

        if (!response.IsSuccessStatusCode)
            throw new Exception($"Not success status code: {response.StatusCode}\n{await response.Content.ReadAsStringAsync()}");
    }
}