namespace Crupest.V2ray;

public class V2rayHttpProxy : IV2rayProxy
{
    public record HttpOutboundJsonObject(string Protocol, SettingsJsonObject Settings, string Tag)
    {
        public static HttpOutboundJsonObject Create(string address, int port, string tag)
        {
            return new HttpOutboundJsonObject("http", new SettingsJsonObject(
                new List<ServerJsonObject> { new ServerJsonObject(address, port) }
            ), tag);
        }
    }

    public record ServerJsonObject(string Address, int Port);
    public record SettingsJsonObject(List<ServerJsonObject> Servers);

    public string Host { get; set; }
    public int Port { get; set; }

    public V2rayHttpProxy(string host, int port)
    {
        Host = host;
        Port = port;
    }

    public HttpOutboundJsonObject ToOutboundJsonObject(string tag = "proxy")
    {
        return HttpOutboundJsonObject.Create(Host, Port, tag);
    }

    object IV2rayProxy.ToOutboundJsonObject()
    {
        return ToOutboundJsonObject();
    }

    public static V2rayHttpProxy FromDictionary(Dictionary<string, string> dict)
    {
        return new V2rayHttpProxy(dict["host"], int.Parse(dict["port"]));
    }
}
