namespace CrupestApi.Commons.Crud;

public interface IColumnMetadata
{

}

[AttributeUsage(AttributeTargets.Property, AllowMultiple = false)]
public class ColumnAttribute : Attribute, IColumnMetadata
{
    // if null, use the property name.
    public string? DatabaseName { get; set; }

    // default false.
    public bool NonNullable { get; set; }

    // default false
    public bool IsPrimaryKey { get; set; }

    public bool IsAutoIncrement { get; set; }
}
