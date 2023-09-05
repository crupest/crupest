namespace Crupest.V2ray;

public class V2rayVmessProxy
{
    public record VmessOutboundJsonObject(string Protocol, SettingsJsonObject Settings, string Tag, StreamSettingsJsonObject StreamSettings)
    {
        public static VmessOutboundJsonObject ByWs(string address, int port, string uuid, string tag, string path)
        {
            return new VmessOutboundJsonObject("vmess", new SettingsJsonObject(
                new List<VnextJsonObject> { new VnextJsonObject(address, port, new List<VnextUserJsonObject> { new VnextUserJsonObject(uuid) }) }
            ), tag, StreamSettingsJsonObject.Ws(path));
        }
    }

    public record SettingsJsonObject(List<VnextJsonObject> Vnext);

    public record VnextJsonObject(string Address, int Port, List<VnextUserJsonObject> Users);

    public record VnextUserJsonObject(string Id, int AlterId = 0, string Security = "auto", int Level = 0);

    public record StreamSettingsJsonObject(string Network, string Security, WsSettingsJsonObject WsSettings)
    {
        public static StreamSettingsJsonObject Ws(string path)
        {
            return new StreamSettingsJsonObject("ws", "tls", new WsSettingsJsonObject(path, new()));
        }
    }

    public record WsSettingsJsonObject(string Path, Dictionary<string, string> Headers);

    public string Host { get; set; }
    public int Port { get; set; }
    public string Path { get; set; }
    public string UserId { get; set; }


    public V2rayVmessProxy(string host, int port, string userId, string path)
    {
        Host = host;
        Port = port;
        UserId = userId;
        Path = path;
    }

    public VmessOutboundJsonObject ToOutboundJsonObject(string tag = "proxy")
    {
        return VmessOutboundJsonObject.ByWs(Host, Port, UserId, tag, Path);
    }

    public static V2rayVmessProxy FromDictionary(Dictionary<string, string> dict)
    {
        return new V2rayVmessProxy(dict["host"], int.Parse(dict["port"]), dict["userid"], dict["path"]);
    }
}
