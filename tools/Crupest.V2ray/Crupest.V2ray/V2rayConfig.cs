using System.Text.Json;
using System.Text.Json.Serialization;

namespace Crupest.V2ray;

public interface IV2rayV4ConfigObject
{
    object ToJsonObjectV4();
}

public class V2rayConfig(Template template, List<V2rayProxy> proxies, V2rayRouting router, V2rayHosts? hosts)
{
    private class JsonInterfaceConverter<Interface> : JsonConverter<Interface>
    {
        public override Interface Read(
            ref Utf8JsonReader reader,
            Type typeToConvert,
            JsonSerializerOptions options)
        {
            throw new NotImplementedException();
        }

        public override void Write(
            Utf8JsonWriter writer,
            Interface value,
            JsonSerializerOptions options)
        {
            JsonSerializer.Serialize(writer, value, typeof(object), options);
        }
    }


    public const string ConfigTemplateFileName = "config.json.template";
    public const string VmessConfigFileName = "vmess.txt";
    public const string ProxyConfigFileName = "proxy.txt";
    public const string HostsConfigFileName = "hosts.txt";

    public static List<string> RequiredConfigFileNames { get; } = [ConfigTemplateFileName, VmessConfigFileName, ProxyConfigFileName];
    public static List<string> ConfigFileNames { get; } = [ConfigTemplateFileName, VmessConfigFileName, ProxyConfigFileName, HostsConfigFileName];

    private const string ProxyAnchor = "PROXY_ANCHOR";
    private const string RoutingAnchor = "ROUTING_ANCHOR";
    private const string HostsAnchor = "HOSTS_ANCHOR";

    public Template Template { get; set; } = template;
    public List<V2rayProxy> Proxies { get; set; } = proxies;
    public V2rayRouting Routing { get; set; } = router;
    public V2rayHosts Hosts { get; set; } = hosts is null ? new V2rayHosts([]) : hosts;

    public string ToJsonStringV4(bool pretty = true)
    {
        var jsonOptions = new JsonSerializerOptions(new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DictionaryKeyPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        });
        jsonOptions.Converters.Add(new JsonInterfaceConverter<V2rayV4ConfigJsonObjects.IOutboundSettings>());
        jsonOptions.Converters.Add(new JsonInterfaceConverter<V2rayV4ConfigJsonObjects.IOutboundStreamSettings>());

        var templateValues = new Dictionary<string, string>
        {
            [ProxyAnchor] = string.Join(',', Proxies.Select(p => JsonSerializer.Serialize(p.ToJsonObjectV4(), jsonOptions))),
            [RoutingAnchor] = JsonSerializer.Serialize(Routing.ToJsonObjectV4(), jsonOptions),
            [HostsAnchor] = JsonSerializer.Serialize(Hosts.ToJsonObjectV4(), jsonOptions),
        };

        var configString = Template.Generate(templateValues);

        if (pretty)
        {
            var jsonOptionsPretty = new JsonSerializerOptions(jsonOptions)
            {
                WriteIndented = true,
            };
            return JsonSerializer.Serialize(JsonSerializer.Deserialize<object>(configString, jsonOptionsPretty), jsonOptionsPretty);
        }
        else
        {
            return configString;
        }
    }

    public static V2rayConfig FromFiles(string templatePath, string vmessPath, string proxyPath, string? hostsPath)
    {
        foreach (var path in new List<string>([templatePath, vmessPath, proxyPath]))
        {
            if (!File.Exists(path))
            {
                throw new FileNotFoundException($"Required config file not found: {path}.");
            }
        }

        string templateString, vmessString, routingString;
        string? hostsString;

        string file = "";
        try
        {
            file = templatePath;
            templateString = File.ReadAllText(templatePath);
            file = vmessPath;
            vmessString = File.ReadAllText(vmessPath);
            file = proxyPath;
            routingString = File.ReadAllText(proxyPath);
            file = proxyPath;
            hostsString = hostsPath is not null ? File.ReadAllText(hostsPath) : null;
        }
        catch (Exception e)
        {
            throw new Exception($"Error reading config file {file}.", e);
        }

        try
        {
            file = templatePath;
            var template = new Template(templateString);
            file = vmessPath;
            var vmess = V2rayVmessProxy.CreateFromConfigString(vmessString, "proxy");
            file = proxyPath;
            var routing = V2rayRouting.CreateFromConfigString(routingString, "proxy");
            file = hostsPath ?? "";
            var hosts = hostsString is not null ? V2rayHosts.CreateFromConfigString(hostsString) : null;
            return new V2rayConfig(template, [vmess], routing, hosts);
        }
        catch (Exception e)
        {
            throw new Exception($"Error parsing config file {file}.", e);
        }
    }

    public static V2rayConfig FromDirectory(string directory)
    {
        return FromFiles(
            Path.Join(directory, ConfigTemplateFileName),
            Path.Join(directory, VmessConfigFileName),
            Path.Join(directory, ProxyConfigFileName),
            Path.Join(directory, HostsConfigFileName)
        );
    }

    public static void FromDirectoryAndWriteToFile(string directory, string outputPath)
    {
        var config = FromDirectory(directory);
        File.WriteAllText(outputPath, config.ToJsonStringV4());
    }
}
