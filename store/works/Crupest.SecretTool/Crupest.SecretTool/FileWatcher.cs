namespace Crupest.SecretTool;

public class FileWatcher(string directory, List<string> fileNames)
{
    public string Directory { get; set; } = directory;
    public List<string> FileNames { get; set; } = fileNames;

    public delegate void OnChangedHandler();
    public event OnChangedHandler? OnChanged;

    public void Run()
    {
        var sourceWatcher = new FileSystemWatcher(Directory);
        foreach (var fileName in FileNames)
        {
            sourceWatcher.Filters.Add(fileName);
        }
        sourceWatcher.NotifyFilter = NotifyFilters.LastWrite;

        while (true)
        {
            var result = sourceWatcher.WaitForChanged(WatcherChangeTypes.Changed | WatcherChangeTypes.Created);
            OnChanged?.Invoke();
        }
    }
}
