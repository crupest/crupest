namespace Crupest.SecretTool;

public static class V5ConfigJsonObjects
{
    public record OutboundObject(string Protocol, object Settings, string Tag, object? StreamSettings)
    {
        public static OutboundObject VmessViaWs(string tag, string address, int port, string uuid, string path)
        {
            return new OutboundObject("vmess", new VmessSettings(address, port, uuid), tag, StreamSettingsObject.Ws(path));
        }

        public static OutboundObject Http(string tag, string address, int port)
        {
            return new OutboundObject("http", new HttpSettingsObject(address, port), tag, null);
        }
    }

    public record WsSettingsObject(string Path, Dictionary<string, string> Headers);

    public record StreamSettingsObject(string Transport, object TransportSettings, string Security, object SecuritySettings)
    {
        public static StreamSettingsObject Ws(string path)
        {
            return new StreamSettingsObject("ws", new WsSettingsObject(path, new()), "tls", new());
        }
    }

    public record VmessSettings(string Address, int Port, string Uuid);

    public record HttpSettingsObject(string Address, int Port);
}
