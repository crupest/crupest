namespace CrupestApi.Commons.Crud;

public interface IColumnMetadata
{

}

public enum ColumnIndexType
{
    None,
    Unique,
    NonUnique
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

    // default false
    public bool IsAutoIncrement { get; set; }

    public ColumnIndexType IndexType { get; set; } = ColumnIndexType.None;

    // Use empty string for default value of string type.
    public bool DefaultEmptyForString { get; set; }
}
