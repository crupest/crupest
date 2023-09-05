namespace Crupest.V2ray;

public class ConfigGenerationWatcher
{
    public ConfigGenerationWatcher() : this(Program.ExeDir, Program.ConfigTemplateFileName, Program.VmessConfigFileName, Program.ProxyConfigFileName, Path.Combine(Program.ExeDir, Program.ConfigOutputFileName), new List<string>())
    {

    }

    public ConfigGenerationWatcher(string directory, string configTemplateFileName, string vmessConfigFileName, string proxyConfigFileName, string configOutputPath, List<string> otherWatchFiles)
    {
        Directory = directory;
        ConfigTemplateFileName = configTemplateFileName;
        VmessConfigFileName = vmessConfigFileName;
        ProxyConfigFileName = proxyConfigFileName;
        ConfigOutputPath = configOutputPath;
        OtherWatchFiles = otherWatchFiles;
    }

    public string Directory { get; set; }
    public string ConfigTemplateFileName { get; set; }
    public string VmessConfigFileName { get; set; }
    public string ProxyConfigFileName { get; set; }
    public List<string> OtherWatchFiles { get; set; }
    public string ConfigOutputPath { get; set; }

    public string ConfigTemplateFilePath => Path.Combine(Directory, ConfigTemplateFileName);
    public string VmessConfigFilePath => Path.Combine(Directory, VmessConfigFileName);
    public string ProxyConfigFilePath => Path.Combine(Directory, ProxyConfigFileName);

    public delegate void OnConfigChangedHandler();

    public void Generate()
    {
        var config = V2rayConfig.FromFiles(ConfigTemplateFilePath, VmessConfigFilePath, ProxyConfigFilePath);

        File.WriteAllText(ConfigOutputPath, config.ToJson());
    }

    public void Run(OnConfigChangedHandler onChanged)
    {
        var sourceWatcher = new FileSystemWatcher(Directory);
        sourceWatcher.Filters.Add(ConfigTemplateFileName);
        sourceWatcher.Filters.Add(VmessConfigFileName);
        sourceWatcher.Filters.Add(ProxyConfigFileName);
        OtherWatchFiles.ForEach((f) => sourceWatcher.Filters.Add(f));
        sourceWatcher.NotifyFilter = NotifyFilters.LastWrite;

        while (true)
        {
            var result = sourceWatcher.WaitForChanged(WatcherChangeTypes.Changed);
            onChanged();
        }
    }
}
