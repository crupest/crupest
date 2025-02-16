namespace Crupest.SecretTool;

public abstract class Proxy(string tag) : IV4ConfigObject, ISingConfigObject
{
    public string Tag { get; set; } = tag;

    public abstract V4ConfigJsonObjects.Outbound ToJsonObjectV4();
    public abstract SingConfigJsonObjects.OutboundBase ToJsonObjectSing();

    object IV4ConfigObject.ToJsonObjectV4()
    {
        return ToJsonObjectV4();
    }

    object ISingConfigObject.ToJsonObjectSing()
    {
        return ToJsonObjectSing();
    }
}

public class HttpProxy(string host, int port, string tag) : Proxy(tag)
{
    public string Host { get; set; } = host;
    public int Port { get; set; } = port;

    public override SingConfigJsonObjects.OutboundBase ToJsonObjectSing()
    {
        throw new NotImplementedException("Http proxy is not supported in sing now.");
    }

    public override V4ConfigJsonObjects.Outbound ToJsonObjectV4()
    {
        return new V4ConfigJsonObjects.Outbound(Tag, "http",
            new V4ConfigJsonObjects.HttpOutboundSettings([new V4ConfigJsonObjects.HttpOutboundServer(Host, Port, [])]),
            null
        );
    }
}


public class VmessProxy(string host, int port, string userId, string path, string tag) : Proxy(tag)
{
    public string Host { get; set; } = host;
    public int Port { get; set; } = port;
    public string Path { get; set; } = path;
    public string UserId { get; set; } = userId;

    public override SingConfigJsonObjects.OutboundBase ToJsonObjectSing()
    {
        return new SingConfigJsonObjects.VmessOutbound(Tag, Host, Port, UserId,
            Transport: new SingConfigJsonObjects.V2rayWebsocketTransport(Path, new Dictionary<string, string> { { "Host", Host } }),
            Tls: new SingConfigJsonObjects.OutboundTls(true));
    }

    public override V4ConfigJsonObjects.Outbound ToJsonObjectV4()
    {
        return new V4ConfigJsonObjects.Outbound(Tag, "vmess",
            new V4ConfigJsonObjects.VmessOutboundSettings(
                [new V4ConfigJsonObjects.VnextServer(Host, Port, [new V4ConfigJsonObjects.VnextServerUser(UserId, 0, "auto", 0)])]),
            new V4ConfigJsonObjects.WsStreamSettings("ws", "tls", new V4ConfigJsonObjects.WsSettings(Path, new() { ["Host"] = Host }))
        );
    }

    public static VmessProxy CreateFromConfigString(string configString, string tag)
    {
        var config = new DictionaryConfig(configString, ["host", "port", "userid", "path"]);
        var portString = config.GetItemCaseInsensitive("port").Value;
        if (!int.TryParse(portString, out var port) || port <= 0)
        {
            throw new FormatException($"Invalid port number: {portString}: not an integer or is a invalid number.");
        }
        return new VmessProxy(config.GetItemCaseInsensitive("host").Value, port,
            config.GetItemCaseInsensitive("userid").Value, config.GetItemCaseInsensitive("path").Value, tag
        );
    }
}
