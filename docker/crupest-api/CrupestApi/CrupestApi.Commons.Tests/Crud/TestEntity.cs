namespace CrupestApi.Commons.Crud.Tests;

public class TestEntity
{
    [Column(NotNull = true)]
    public string Name { get; set; } = default!;

    [Column(NotNull = true)]
    public int Age { get; set; }

    [Column]
    public float? Height { get; set; }

    public string NonColumn { get; set; } = "Not A Column";
}
