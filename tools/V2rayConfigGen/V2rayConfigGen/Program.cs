using System.Reflection;

namespace Crupest.V2ray;

public static class Program
{
    public const string ConfigTemplateFile = "config.json.template";
    public const string VmessConfigFile = "vmess.txt";
    public const string ProxyGeoSitesFile = "proxy.txt";

    public static void Main(string[] args)
    {
        var exeLocation = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        var config = V2rayConfig.FromFiles(
            Path.Combine(exeLocation, ConfigTemplateFile),
            Path.Combine(exeLocation, VmessConfigFile),
            Path.Combine(exeLocation, ProxyGeoSitesFile)
        );

        Console.Write(config.ToJson());
    }
}
