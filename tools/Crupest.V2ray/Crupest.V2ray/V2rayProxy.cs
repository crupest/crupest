namespace Crupest.V2ray;

public abstract class V2rayProxy(string tag) : IV2rayV4ConfigObject
{
    public string Tag { get; set; } = tag;

    public abstract V2rayV4ConfigJsonObjects.Outbound ToJsonObjectV4();

    object IV2rayV4ConfigObject.ToJsonObjectV4()
    {
        return ToJsonObjectV4();
    }
}

public class V2rayHttpProxy(string host, int port, string tag) : V2rayProxy(tag)
{
    public string Host { get; set; } = host;
    public int Port { get; set; } = port;

    public override V2rayV4ConfigJsonObjects.Outbound ToJsonObjectV4()
    {
        return new V2rayV4ConfigJsonObjects.Outbound(Tag, "http",
            new V2rayV4ConfigJsonObjects.HttpOutboundSettings([new V2rayV4ConfigJsonObjects.HttpOutboundServer(Host, Port, [])]),
            null
        );
    }
}


public class V2rayVmessProxy(string host, int port, string userId, string path, string tag) : V2rayProxy(tag)
{
    public string Host { get; set; } = host;
    public int Port { get; set; } = port;
    public string Path { get; set; } = path;
    public string UserId { get; set; } = userId;

    public override V2rayV4ConfigJsonObjects.Outbound ToJsonObjectV4()
    {
        return new V2rayV4ConfigJsonObjects.Outbound(Tag, "vmess",
            new V2rayV4ConfigJsonObjects.VmessOutboundSettings(
                [new V2rayV4ConfigJsonObjects.VnextServer(Host, Port, [new V2rayV4ConfigJsonObjects.VnextServerUser(UserId, 0, "auto", 0)])]),
            new V2rayV4ConfigJsonObjects.WsStreamSettings("ws", "tls", new V2rayV4ConfigJsonObjects.WsSettings(Path, new() { ["Host"] = Host }))
        );
    }

    public static V2rayVmessProxy CreateFromConfigString(string configString, string tag)
    {
        var config = new DictionaryConfig(configString, ["host", "port", "userid", "path"]);
        var portString = config.GetItemCaseInsensitive("port").Value;
        if (!int.TryParse(portString, out var port) || port <= 0)
        {
            throw new FormatException($"Invalid port number: {portString}: not an integer or is a invalid number.");
        }
        return new V2rayVmessProxy(config.GetItemCaseInsensitive("host").Value, port,
            config.GetItemCaseInsensitive("userid").Value, config.GetItemCaseInsensitive("path").Value, tag
        );
    }
}
