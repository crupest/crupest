using System.Collections.Immutable;
using System.Diagnostics;

namespace Crupest.Service.Docker;

public class DockerCommandFailedException : Exception
{
    public DockerCommandFailedException(DockerCommandResult result, string message, Exception? inner)
        : base(message, inner)
    {
        Result = result;
    }

    public DockerCommandResult Result { get; }

    public static void CheckDockerCommandResult(DockerCommandResult result, string message, Exception? inner)
    {
        if (!result.Success)
        {
            throw new DockerCommandFailedException(result, message, inner);
        }
    }
}

public class DockerCommandResult
{
    public DockerCommandResult(DockerContext context, IEnumerable<string> args, bool success, int exitCode, bool isTimeout, string output, string errorOutput)
    {
        Context = context;
        CommandArgs = args.ToImmutableList();
        Success = success;
        ExitCode = exitCode;
        IsTimeout = isTimeout;
        Output = output;
        ErrorOutput = errorOutput;
    }

    public DockerContext Context { get; }

    public IReadOnlyList<string> CommandArgs { get; }

    public bool Success { get; }
    public int ExitCode { get; }
    public bool IsTimeout { get; }
    public string Output { get; }
    public string ErrorOutput { get; set; }
}

public class DockerContext
{
    public string DockerCliExecutable { get; set; } = "docker";

    public TimeSpan DockerCommandTimeout { get; set; } = TimeSpan.FromSeconds(30);

    public async Task<DockerCommandResult> RunDockerCommandAsync(IEnumerable<string> args, CancellationToken cancellationToken = default(CancellationToken))
    {
        var processStartInfo = new ProcessStartInfo(DockerCliExecutable);
        foreach (var arg in args)
        {
            processStartInfo.ArgumentList.Add(arg);
        }
        processStartInfo.RedirectStandardOutput = true;
        processStartInfo.RedirectStandardError = true;

        cancellationToken.ThrowIfCancellationRequested();

        using var process = new Process();
        process.StartInfo = processStartInfo;

        cancellationToken.ThrowIfCancellationRequested();
        Task processTask = Task.Run(() => {
        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        process.
                })
        

        if (exit)
        {
            var result = new DockerCommandResult(this, args,
                    process.ExitCode == 0, process.ExitCode, false,
                    process.StandardOutput.ReadToEnd(), process.StandardError.ReadToEnd());
            return result;
        }
        else
        {
            process.Kill();
            var result = new DockerCommandResult(this, args,
                    false, process.ExitCode, true,
                    process.StandardOutput.ReadToEnd(), process.StandardOutput.ReadToEnd());
            return result;
        }
    }
}

public interface IDockerImage
{
    /// <summary>
    /// The full name of the image, which can be used to create a container.
    /// </summary>
    string FullName { get; }

    string Name { get; }
    string Tag { get; set; }

    /// <summary>
    /// Build or pull the image, so it can be used.
    /// </summary>
    /// <returns>The completion task.</returns>
    Task Make(DockerContext context);
}

public class DockerRegistryImage
{
    public DockerRegistryImage(string name, string? tag = null)
    {
        Name = name;
        Tag = tag;
    }

    public string Name { get; set; }
    public string? Tag { get; set; }

    public string FullName => Tag is null ? Name : $"{Name}:{Tag}";

    public async Task Make(DockerContext context) 
    {
await context.RunDockerCommandAsync("")
    }

}

public class DockerService
{


}
