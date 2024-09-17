using System.Diagnostics;

namespace Crupest.V2ray;

public class V2rayController(string executablePath, string configPath, string? assetPath)
{
    public const string V2rayAssetEnvironmentVariableName = "v2ray.location.asset";

    public static string? FindExecutable(string contentDir, out bool isLocal, string? executableName = null)
    {
        isLocal = false;
        executableName ??= "v2ray";

        if (OperatingSystem.IsWindows())
        {
            executableName += ".exe";
        }

        var localV2rayPath = Path.Combine(contentDir, executableName);
        if (File.Exists(localV2rayPath))
        {
            isLocal = true;
            return localV2rayPath;
        }

        var paths = Environment.GetEnvironmentVariable("PATH")?.Split(Path.PathSeparator);
        if (paths is not null)
        {
            foreach (var p in paths)
            {
                var v2rayPath = Path.Combine(p, executableName);
                if (File.Exists(v2rayPath))
                {
                    return v2rayPath;
                }
            }
        }

        return null;
    }

    public string ExecutablePath { get; } = executablePath;
    public string ConfigPath { get; } = configPath;
    public string? AssetPath { get; } = assetPath;
    public Process? CurrentProcess { get; private set; }

    private Process CreateProcess()
    {
        var process = new Process();

        var startInfo = new ProcessStartInfo
        {
            FileName = ExecutablePath,
        };
        startInfo.ArgumentList.Add("run");
        startInfo.ArgumentList.Add("-c");
        startInfo.ArgumentList.Add(ConfigPath);
        if (AssetPath is not null)
        {
            startInfo.EnvironmentVariables[V2rayAssetEnvironmentVariableName] = AssetPath;
        }

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
                    const string message = "V2ray exited with error.";
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
