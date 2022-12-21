namespace CrupestApi.Commons.Crud.Tests;

public class TestEntity
{
    [Column(ActAsKey = true, NotNull = true)]
    public string Name { get; set; } = default!;

    [Column(NotNull = true)]
    public int Age { get; set; }

    [Column]
    public float? Height { get; set; }

    [Column(Generated = true, NotNull = true, NoUpdate = true)]
    public string Secret { get; set; } = default!;

    public static string SecretDefaultValueGenerator()
    {
        return "secret";
    }

    public string NonColumn { get; set; } = "Not A Column";
}
