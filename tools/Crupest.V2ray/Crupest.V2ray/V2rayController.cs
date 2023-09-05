using System.Diagnostics;

namespace Crupest.V2ray;

public class V2rayController
{
    public const string V2RayAssetLocationEnvironmentVariableName = "V2RAY_LOCATION_ASSET";
    public const string V2RayConfigLocationEnvironmentVariableName = "V2RAY_LOCATION_CONFIG";

    public V2rayController(string v2rayExePath = "v2ray") : this(v2rayExePath, Program.ExeDir, Program.ExeDir)
    {

    }

    public V2rayController(string v2rayExePath, string configDirPath, string assetDirPath)
    {
        V2rayExePath = v2rayExePath;
        ConfigDirPath = configDirPath;
        AssetDirPath = assetDirPath;
    }

    public string V2rayExePath { get; }
    public string ConfigDirPath { get; }
    public string AssetDirPath { get; }
    public Process? CurrentProcess { get; private set; }

    private Process CreateProcess()
    {
        var process = new Process();

        var startInfo = new ProcessStartInfo
        {
            FileName = V2rayExePath,
        };
        startInfo.EnvironmentVariables[V2RayConfigLocationEnvironmentVariableName] = ConfigDirPath;
        startInfo.EnvironmentVariables[V2RayAssetLocationEnvironmentVariableName] = AssetDirPath;

        process.StartInfo = startInfo;
        process.OutputDataReceived += (_, args) =>
        {
            Console.Out.Write(args.Data);
        };
        process.ErrorDataReceived += (_, args) =>
        {
            Console.Error.WriteLine(args.Data);
        };

        return process;
    }

    public void Stop()
    {
        if (CurrentProcess is not null)
        {
            CurrentProcess.Kill();
            CurrentProcess.Dispose();
            CurrentProcess = null;
            Console.WriteLine("V2ray stopped.");
        }
    }

    public void Start(bool stopOld = false)
    {
        if (stopOld) Stop();

        if (CurrentProcess is null)
        {
            CurrentProcess = CreateProcess();
            CurrentProcess.EnableRaisingEvents = true;
            CurrentProcess.Exited += (_, _) =>
            {
                if (CurrentProcess.ExitCode != 0)
                {
                    const string message = "V2ray exits with error.";
                    Console.Error.WriteLine(message);
                    throw new Exception(message);
                }
            };
            CurrentProcess.Start();
            Console.WriteLine("V2ray started.");
        }
    }

    public void Restart()
    {
        Start(true);
    }
}
