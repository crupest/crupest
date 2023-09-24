namespace Crupest.V2ray;

public record V2rayHostRule(string Origin, List<string> Resolved)
{
    public static V2rayHostRule Parse(string str)
    {
        var segments = str.Split(' ', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        if (segments.Length == 1)
        {
            throw new Exception("Host rule only contains 1 segment.");
        }

        var resolved = new List<string>();
        resolved.AddRange(segments[1..]);

        return new V2rayHostRule(segments[0], resolved);
    }
}

