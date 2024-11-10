namespace CrupestApi.Commons.Crud;

/// <summary>
/// This will always represent null value in database.
/// </summary>
public class DbNullValue
{
    public static DbNullValue Instance { get; } = new DbNullValue();
}