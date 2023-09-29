using System.Diagnostics;

namespace Crupest.Service.Utility;

public class WrappedProcess : IProcess
{
    public WrappedProcess()
    {

    }

    public Process UnderlyingValue { get; } = new Process();

    public ProcessStartInfo StartInfo
    {
        get { return UnderlyingValue.StartInfo; }
        set { UnderlyingValue.StartInfo = value; }
    }

    public bool HasExited => UnderlyingValue.HasExited;

    public int ExitCode => UnderlyingValue.ExitCode;

    public bool Start() => UnderlyingValue.Start();

    public void Kill() => UnderlyingValue.Kill();

    public void WaitForExit() => UnderlyingValue.WaitForExit();

    public bool WaitForExit(TimeSpan timeout) => UnderlyingValue.WaitForExit(timeout);

    public void Dispose() => UnderlyingValue.Dispose();

    public event DataReceivedEventHandler OutputDataReceived { add { UnderlyingValue.OutputDataReceived += value; } remove { UnderlyingValue.OutputDataReceived -= value; } }
    public event DataReceivedEventHandler ErrorDataReceived { add { UnderlyingValue.ErrorDataReceived += value; } remove { UnderlyingValue.ErrorDataReceived -= value; } }
}


