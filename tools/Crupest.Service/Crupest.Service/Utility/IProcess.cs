using System.Diagnostics;

namespace Crupest.Service.Utility;

public interface IProcess : IDisposable
{
    ProcessStartInfo StartInfo { get; set; }
    bool HasExited { get; }
    int ExitCode { get; }
    bool Start();
    void Kill();
    void WaitForExit();
    bool WaitForExit(TimeSpan timeout);

    event DataReceivedEventHandler OutputDataReceived;
    event DataReceivedEventHandler ErrorDataReceived;
}


