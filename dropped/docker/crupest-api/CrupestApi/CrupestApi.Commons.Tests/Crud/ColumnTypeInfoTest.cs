using System.Data;

namespace CrupestApi.Commons.Crud.Tests;

public class ColumnTypeInfoTest
{
    private ColumnTypeProvider _provider = new ColumnTypeProvider();

    [Theory]
    [InlineData(typeof(int), DbType.Int32, 123)]
    [InlineData(typeof(long), DbType.Int64, 456)]
    [InlineData(typeof(sbyte), DbType.SByte, 789)]
    [InlineData(typeof(short), DbType.Int16, 101)]
    [InlineData(typeof(float), DbType.Single, 1.0f)]
    [InlineData(typeof(double), DbType.Double, 1.0)]
    [InlineData(typeof(string), DbType.String, "Hello world!")]
    [InlineData(typeof(byte[]), DbType.Binary, new byte[] { 1, 2, 3 })]
    public void BasicColumnTypeTest(Type type, DbType dbType, object? value)
    {
        var typeInfo = _provider.Get(type);
        Assert.True(typeInfo.IsSimple);
        Assert.Equal(dbType, typeInfo.DbType);
        Assert.Equal(value, typeInfo.ConvertFromDatabase(value));
        Assert.Equal(value, typeInfo.ConvertToDatabase(value));
    }

    [Fact]
    public void DateTimeColumnTypeTest()
    {
        var dateTimeColumnTypeInfo = _provider.Get(typeof(DateTime));
        Assert.Equal(typeof(DateTime), dateTimeColumnTypeInfo.ClrType);
        Assert.Equal(typeof(string), dateTimeColumnTypeInfo.DatabaseClrType);

        var dateTime = new DateTime(2000, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        var dateTimeString = "2000-01-01T00:00:00Z";
        Assert.Equal(dateTimeString, dateTimeColumnTypeInfo.ConvertToDatabase(dateTime));
        Assert.Equal(dateTime, dateTimeColumnTypeInfo.ConvertFromDatabase(dateTimeString));
    }
}
