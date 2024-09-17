namespace Crupest.V2ray;

public static class V2rayV4ConfigJsonObjects
{
    public interface IObject;
    public interface IOutboundSettings : IObject;
    public interface IOutboundStreamSettings : IObject;

    public record WsSettings(string Path, Dictionary<string, string> Headers) : IObject;
    public record WsStreamSettings(string Network, string Security, WsSettings WsSettings) : IOutboundStreamSettings;
    public record VnextServerUser(string Id, int AlterId, string Security, int Level) : IObject;
    public record VnextServer(string Address, int Port, List<VnextServerUser> Users) : IObject;
    public record VmessOutboundSettings(List<VnextServer> Vnext) : IOutboundSettings;
    public record HttpOutboundUser(string User, string Pass) : IObject;
    public record HttpOutboundServer(string Address, int Port, List<HttpOutboundUser> Users) : IObject;
    public record HttpOutboundSettings(List<HttpOutboundServer> Servers) : IOutboundSettings;
    public record Outbound(string Tag, string Protocol, IOutboundSettings Settings,
        IOutboundStreamSettings? StreamSettings) : IObject;

    public record RoutingRule(string DomainMatcher = "mph", string Type = "field", List<string>? Domains = null, List<string>? Ip = null,
        string? Port = null, string? SourcePort = null, string? Network = null, List<string>? Source = null,
        List<string>? User = null, List<string>? InboundTag = null, List<string>? Protocol = null, string? Attrs = null,
        string? OutboundTag = null, string? BalancerTag = null) : IObject;
    public record Routing(List<RoutingRule> Rules, string DomainStrategy = "IpOnDemand", string DomainMatcher = "mph") : IObject;
}
