using System.Collections.Immutable;
using System.Diagnostics;
using System.Text;

namespace Crupest.Service.Utility;

public class SubProcess
{
    private IProcessFactory _processFactory;
    private ProcessStartInfo _processStartInfo;
    private IProcess _process;
    private StringBuilder _output = new StringBuilder();
    private StringBuilder _errorOutput = new StringBuilder();
    private SubProcessExitReason _exitReason = SubProcessExitReason.Normal;
    private Task? _processWaitTask;

    public SubProcess(SubProcessOptions options)
        : this(WrappedProcessFactory.Instance, options)
    {

    }

    public SubProcess(IProcessFactory processFactory, SubProcessOptions options)
    {
        _processFactory = processFactory;
        _processStartInfo = CreateProcessStartInfo(options);
        _process = CreateProcess();
        _process.StartInfo = _processStartInfo;
    }

    public string Executable => _processStartInfo.FileName;
    public IReadOnlyList<string> Arguments => _processStartInfo.ArgumentList.ToImmutableList();
    public IReadOnlyDictionary<string, string?> Environment => _processStartInfo.Environment.ToImmutableDictionary();

    public SubProcessState State { get; private set; } = SubProcessState.Created;
    public SubProcessResult? Result { get; private set; }

    private ProcessStartInfo CreateProcessStartInfo(SubProcessOptions options)
    {
        var startInfo = new ProcessStartInfo();
        startInfo.FileName = options.Executable;
        foreach (var argument in options.Arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }
        foreach (var (name, value) in options.Environment)
        {
            startInfo.Environment.Add(name, value);
        }
        if (options.WorkingDirectory is not null)
        {
            startInfo.WorkingDirectory = options.WorkingDirectory;
        }
        startInfo.CreateNoWindow = true;
        startInfo.StandardInputEncoding = options.InputEncoding;
        startInfo.StandardOutputEncoding = options.OutputEncoding;
        startInfo.StandardErrorEncoding = options.ErrorOutputEncoding;
        startInfo.RedirectStandardInput = true;
        startInfo.RedirectStandardOutput = true;
        startInfo.RedirectStandardError = true;

        return startInfo;
    }

    private void OnProcessOutput(object sender, DataReceivedEventArgs args)
    {
        _output.AppendLine(args.Data);
    }


    private void OnProcessError(object sender, DataReceivedEventArgs args)
    {
        _errorOutput.AppendLine(args.Data);
    }

    private IProcess CreateProcess()
    {
        var process = _processFactory.Create();
        process.StartInfo = _processStartInfo;

        process.OutputDataReceived += this.OnProcessOutput;
        process.ErrorDataReceived += this.OnProcessError;

        return process;
    }

    private SubProcessResult GenerateResult()
    {
        return new SubProcessResult(_process.ExitCode, _exitReason, _output.ToString(), _errorOutput.ToString());
    }

    private void ForceStopInternal(bool isTimeout)
    {
        if (_process.HasExited) return;
        _exitReason = isTimeout ? SubProcessExitReason.Timeout : SubProcessExitReason.Canceled;
        _process.Kill();
    }

    public Task<SubProcessResult> Run(CancellationToken cancellationToken = default)
    {
        return Run(null, cancellationToken);
    }

    public async Task<SubProcessResult> Run(TimeSpan? timeout, CancellationToken cancellationToken = default)
    {
        if (State != SubProcessState.Created)
        {
            throw new InvalidOperationException("SubProcess is already running or has exited.");
        }

        State = SubProcessState.Running;
        _process.Start();


        if (cancellationToken.IsCancellationRequested)
        {
            ForceStopInternal(false);
        }
        else
        {
            cancellationToken.Register(() => ForceStopInternal(false));
        }

        await Task.Run(() =>
        {
            if (timeout.HasValue)
            {
                var exit = _process.WaitForExit(timeout.Value);
                if (!exit) ForceStopInternal(true);
            }
            else
            {
                _process.WaitForExit();
            }
            State = SubProcessState.Exited;
        });

        Result = GenerateResult();
        return Result;
    }
}


