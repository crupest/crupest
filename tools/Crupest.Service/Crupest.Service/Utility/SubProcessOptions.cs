using System.Text;

namespace Crupest.Service.Utility;

public class SubProcessOptions
{
    public SubProcessOptions(string executable)
    {
        Executable = executable;
    }

    public string Executable { get; set; }
    public IList<string> Arguments { get; set; } = new List<string>();
    public IDictionary<string, string?> Environment { get; set; } = new Dictionary<string, string?>();
    public string? WorkingDirectory { get; set; }
    public Encoding? InputEncoding { get; set; }
    public Encoding? OutputEncoding { get; set; }
    public Encoding? ErrorOutputEncoding { get; set; }
}


