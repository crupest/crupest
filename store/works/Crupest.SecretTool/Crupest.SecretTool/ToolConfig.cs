using System.Text.Json;
using System.Text.Json.Serialization;

namespace Crupest.SecretTool;

public interface IV4ConfigObject
{
    object ToJsonObjectV4();
}

public interface ISingConfigObject
{
    object ToJsonObjectSing();
}

public class ToolConfigBase(Template template, List<Proxy> proxies, Routing router)
{
    protected class JsonInterfaceConverter<Interface> : JsonConverter<Interface>
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

    public const string VmessConfigFileName = "vmess.txt";
    public const string ProxyConfigFileName = "proxy.txt";

    public Template Template { get; set; } = template;
    public List<Proxy> Proxies { get; set; } = proxies;
    public Routing Routing { get; set; } = router;
}

public class ToolConfig(Template template, List<Proxy> proxies, Routing router, StaticHosts? hosts) : ToolConfigBase(template, proxies, router)
{
    public const string ConfigTemplateFileName = "config.json.template";
    public const string HostsConfigFileName = "hosts.txt";

    public static List<string> RequiredConfigFileNames { get; } = [ConfigTemplateFileName, VmessConfigFileName, ProxyConfigFileName];
    public static List<string> ConfigFileNames { get; } = [ConfigTemplateFileName, VmessConfigFileName, ProxyConfigFileName, HostsConfigFileName];

    private const string ProxyAnchor = "PROXY_ANCHOR";
    private const string RoutingAnchor = "ROUTING_ANCHOR";
    private const string HostsAnchor = "HOSTS_ANCHOR";

    public const string AddCnAttributeToGeositeEnvironmentVariable = "CRUPEST_V2RAY_GEOSITE_USE_CN";

    private static bool UseCnGeoSite => Environment.GetEnvironmentVariable(AddCnAttributeToGeositeEnvironmentVariable) switch
    {
        "0" or "false" or "off" or "disable" => false,
        _ => true
    };

    public StaticHosts Hosts { get; set; } = hosts is null ? new StaticHosts([]) : hosts;

    public string ToJsonStringV4(string domainStrategy = "IpOnDemand", bool directGeositeCn = true, bool pretty = true)
    {
        var jsonOptions = new JsonSerializerOptions(new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DictionaryKeyPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        });
        // TODO: Make interface converter generic.
        jsonOptions.Converters.Add(new JsonInterfaceConverter<V4ConfigJsonObjects.IOutboundSettings>());
        jsonOptions.Converters.Add(new JsonInterfaceConverter<V4ConfigJsonObjects.IOutboundStreamSettings>());

        var templateValues = new Dictionary<string, string>
        {
            [ProxyAnchor] = string.Join(',', Proxies.Select(p => JsonSerializer.Serialize(p.ToJsonObjectV4(), jsonOptions))),
            [RoutingAnchor] = JsonSerializer.Serialize(Routing.ToJsonObjectV4(domainStrategy, directGeositeCn), jsonOptions),
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

    public static ToolConfig FromFiles(string templatePath, string vmessPath, string proxyPath, string? hostsPath)
    {
        foreach (var path in new List<string>([templatePath, vmessPath, proxyPath]))
        {
            if (!File.Exists(path))
            {
                throw new FileNotFoundException($"Required config file not found: {path}.");
            }
        }

        ProxyFile proxyFile = new(proxyPath);
        string templateString, vmessString;
        string? hostsString;

        string file = "";
        try
        {
            file = templatePath;
            templateString = File.ReadAllText(templatePath);
            file = vmessPath;
            vmessString = File.ReadAllText(vmessPath);
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
            var vmess = VmessProxy.CreateFromConfigString(vmessString, "proxy");
            file = proxyPath;
            var routing = Routing.FromProxyFile(proxyFile, "proxy");
            file = hostsPath ?? "";
            var hosts = hostsString is not null ? StaticHosts.CreateFromHostMatchConfigString(hostsString) : null;
            return new ToolConfig(template, [vmess], routing, hosts);
        }
        catch (Exception e)
        {
            throw new Exception($"Error parsing config file {file}.", e);
        }
    }

    public static ToolConfig FromDirectory(string directory)
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

public class SingToolConfig(Template template, List<Proxy> proxies, Routing router, string inboundsString) : ToolConfigBase(template, proxies, router)
{

    public const string ConfigTemplateFileName = "sing-config.json.template";
    public const string ConfigInboundsPcFileName = "sing-inbounds-pc.json";
    public const string ConfigInboundsMobileFileName = "sing-inbounds-mobile.json";

    public static List<string> RequiredConfigFileNames { get; } = [ConfigTemplateFileName, VmessConfigFileName, ProxyConfigFileName, ConfigInboundsMobileFileName, ConfigInboundsPcFileName];

    private const string ProxyAnchor = "PROXY_ANCHOR";
    private const string RouteAnchor = "ROUTE_ANCHOR";
    private const string InboundsAnchor = "INBOUNDS_ANCHOR";

    public string InboundsString { get; } = inboundsString;

    public string ToSingConfigString(bool pretty = true)
    {
        var jsonOptions = new JsonSerializerOptions(new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            DictionaryKeyPolicy = JsonNamingPolicy.SnakeCaseLower,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        });
        // TODO: Make interface converter generic.
        jsonOptions.Converters.Add(new JsonInterfaceConverter<SingConfigJsonObjects.OutboundBase>());
        jsonOptions.Converters.Add(new JsonInterfaceConverter<SingConfigJsonObjects.V2rayTransportBase>());

        var templateValues = new Dictionary<string, string>
        {
            [ProxyAnchor] = string.Join(',', Proxies.Select(p => JsonSerializer.Serialize(p.ToJsonObjectSing(), jsonOptions))),
            [RouteAnchor] = JsonSerializer.Serialize(Routing.ToJsonObjectSing(), jsonOptions),
            [InboundsAnchor] = InboundsString
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

    public static SingToolConfig FromFiles(string templatePath, string vmessPath, string proxyPath, string inboundsPath, bool clean, bool silent)
    {
        foreach (var path in new List<string>([templatePath, vmessPath, proxyPath, inboundsPath]))
        {
            if (!File.Exists(path))
            {
                throw new FileNotFoundException($"Required config file not found: {path}.");
            }
        }

        var geoSiteData = GeoDataManager.Instance.GetOrCreateGeoSiteData(clean, silent);

        ProxyFile proxyFile = new(proxyPath);
        string templateString, vmessString, inboundsString;

        string file = "";
        try
        {
            file = templatePath;
            templateString = File.ReadAllText(templatePath);
            file = vmessPath;
            vmessString = File.ReadAllText(vmessPath);
            file = inboundsPath;
            inboundsString = File.ReadAllText(inboundsPath);
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
            var vmess = VmessProxy.CreateFromConfigString(vmessString, "proxy-out");
            file = proxyPath;
            var routing = Routing.FromProxyFileForSing(proxyFile, geoSiteData, "proxy-out", "direct-out");
            return new SingToolConfig(template, [vmess], routing, inboundsString);
        }
        catch (Exception e)
        {
            throw new Exception($"Error parsing config file {file}.", e);
        }
    }

    public static SingToolConfig FromDirectory(string directory, bool isMobile, bool clean, bool silent)
    {
        return FromFiles(
            Path.Join(directory, ConfigTemplateFileName),
            Path.Join(directory, VmessConfigFileName),
            Path.Join(directory, ProxyConfigFileName),
            isMobile ? Path.Join(directory, ConfigInboundsMobileFileName) : Path.Join(directory, ConfigInboundsPcFileName),
            clean, silent
        );
    }
}
