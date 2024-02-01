using System.Diagnostics;

namespace Crupest.V2ray;

public class V2rayController
{
    public static string V2rayExecutableName { get; } = OperatingSystem.IsWindows() ? "v2ray.exe" : "v2ray";
    public const string V2rayExecutableLocationEnvironmentVariableName = "V2RAY_LOCATION_EXE";
    public const string V2rayAssetLocationEnvironmentVariableName = "V2RAY_LOCATION_ASSET";
    public const string V2rayConfigLocationEnvironmentVariableName = "V2RAY_LOCATION_CONFIG";
    public const string V2rayV5ConfdirEnvironmentVariableName = "v2ray.location.confdir";

    public V2rayController() : this(V2rayExecutableName, Program.ExeDir, Program.ExeDir)
    {
        var localV2ray = Path.Combine(Program.ExeDir, V2rayExecutableName);
        if (Path.Exists(localV2ray))
        {
            V2rayExePath = localV2ray;
        }
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
        startInfo.EnvironmentVariables[V2rayConfigLocationEnvironmentVariableName] = ConfigDirPath;
        startInfo.EnvironmentVariables[V2rayAssetLocationEnvironmentVariableName] = AssetDirPath;

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

    private Process V5CreateProcess()
    {
        var process = new Process();

        var startInfo = new ProcessStartInfo
        {
            FileName = V2rayExePath,
        };
        startInfo.ArgumentList.Add("run");
        startInfo.EnvironmentVariables[V2rayV5ConfdirEnvironmentVariableName] = ConfigDirPath;

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
            CurrentProcess = V5CreateProcess();
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
