namespace Crupest.Service.Utility;

public class WrappedProcessFactory : IProcessFactory
{
    public static WrappedProcessFactory Instance { get; } = new WrappedProcessFactory();

    public IProcess Create() => new WrappedProcess();
}


