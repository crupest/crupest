namespace Crupest.Service.Utility;

public class SubProcessResult
{
    public SubProcessResult(int exitCode, SubProcessExitReason exitReason, string output, string errorOutput)
    {
        ExitCode = exitCode;
        ExitReason = exitReason;
        Output = output;
        ErrorOutput = errorOutput;
    }

    public int ExitCode { get; }
    public SubProcessExitReason ExitReason { get; }
    public bool Success => ExitCode == 0;

    public string Output { get; }
    public string ErrorOutput { get; }
}


