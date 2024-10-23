namespace Crupest.SecretTool;

public static class SingConfigJsonObjects
{
    public interface IObject;

    public record OutboundTls(bool Enabled);
    public record V2rayTransportBase(string Type);
    public record V2rayWebsocketTransport(string Path, Dictionary<string, string>? Headers = null) : V2rayTransportBase("ws");
    public record OutboundBase(string Tag, string Type) : IObject;
    public record VmessOutbound(string Tag, string Server, int ServerPort, string Uuid, string Security = "auto",
        V2rayTransportBase? Transport = null, OutboundTls? Tls = null): OutboundBase(Tag, "vmess");

    public record RouteRule(List<string>? Domain = null, List<string>? DomainSuffix = null, List<string>? DomainKeyword = null,
        List<string>? DomainRegex = null, List<string>? IpCidr = null, List<string>? SourceIpCidr = null,
         List<int>? Port = null, List<int>? SourcePort = null, List<string>? PortRange = null, List<string>? SourcePortRange = null,
         string? Network = null, List<string>? Inbound = null, string? Outbound = null) : IObject;

    public record Route(List<RouteRule> Rules) : IObject;
}
