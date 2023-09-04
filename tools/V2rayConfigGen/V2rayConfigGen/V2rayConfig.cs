using System.Text.Json;

namespace Crupest.V2ray;

public class V2rayConfig
{
    private const string VmessAnchor = "VMESS_PROXY_ANCHOR";
    private const string RoutingAnchor = "ROUTING_ANCHOR";

    public V2rayConfig(string template, V2rayVmessProxy vmess, V2rayRouting router) {
        Template = template;
        Vmess = vmess;
        Routing = router;
    }

    public string Template { get; set; }
    public V2rayVmessProxy Vmess { get; set; }
    public V2rayRouting Routing { get; set; }

    public string ToJson(bool pretty = true)
    {
        var jsonOptions = new JsonSerializerOptions(new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DictionaryKeyPolicy = JsonNamingPolicy.CamelCase,
        });

        var templateValues = new Dictionary<string, string>
        {
            [VmessAnchor] = JsonSerializer.Serialize(Vmess.ToOutboundJsonObject(), jsonOptions),
            [RoutingAnchor] = JsonSerializer.Serialize(Routing.ToJsonObject(), jsonOptions)
        };

        return FileUtility.JsonFormat(FileUtility.TextFromTemplate(Template, templateValues));
    }

    public static V2rayConfig FromFiles(string templatePath, string vmessPath, string routingPath)
    {
        var template = File.ReadAllText(templatePath);
        var vmessDict = FileUtility.ReadDictionaryFile(vmessPath);
        var proxyRoutingList = FileUtility.ReadListFile(routingPath);

        var vmess = V2rayVmessProxy.FromDictionary(vmessDict);
        var routing = V2rayRouting.FromStringList(proxyRoutingList);

        return new V2rayConfig(template, vmess, routing);
    }
}
