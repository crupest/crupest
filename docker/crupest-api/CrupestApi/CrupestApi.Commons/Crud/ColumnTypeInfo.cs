using System.Data;
using System.Diagnostics;
using System.Text.Json.Serialization;

namespace CrupestApi.Commons.Crud;

// TODO: Implement this.
public interface IColumnTypeInfo
{
    Type ClrType { get; }
    Type DatabaseClrType { get; }
    DbType DbType { get; }

    string GetSqlTypeString(string? dbProviderId = null)
    {
        // Default implementation for SQLite
        return DbType switch
        {
            DbType.String => "TEXT",
            DbType.Int16 or DbType.Int32 or DbType.Int64 => "INTEGER",
            DbType.Double => "REAL",
            DbType.Binary => "BLOB",
            _ => throw new Exception($"Unsupported DbType: {DbType}"),
        };
    }

    JsonConverter? JsonConverter { get; }

    // You must override this method if ClrType != DatabaseClrType
    object? ConvertFromDatabase(object? databaseValue)
    {
        Debug.Assert(ClrType == DatabaseClrType);
        return databaseValue;
    }

    // You must override this method if ClrType != DatabaseClrType
    object? ConvertToDatabase(object? value)
    {
        Debug.Assert(ClrType == DatabaseClrType);
        return value;
    }
}

// TODO: Implement and register this service.
public interface IColumnTypeProvider
{
    IColumnTypeInfo Get(Type clrType);
}
