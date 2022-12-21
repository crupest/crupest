using Microsoft.Extensions.Logging.Abstractions;

namespace CrupestApi.Commons.Crud.Tests;

public class TableInfoTest
{
    private static TableInfoFactory TableInfoFactory = new TableInfoFactory(new ColumnTypeProvider(), NullLoggerFactory.Instance);

    private TableInfo _tableInfo;

    public TableInfoTest()
    {
        _tableInfo = TableInfoFactory.Get(typeof(TestEntity));
    }

    [Fact]
    public void TestColumnCount()
    {
        Assert.Equal(5, _tableInfo.Columns.Count);
        Assert.Equal(4, _tableInfo.PropertyColumns.Count);
        Assert.Equal(4, _tableInfo.ColumnProperties.Count);
        Assert.Equal(1, _tableInfo.NonColumnProperties.Count);
    }

    [Fact]
    public void GenerateSelectSqlTest()
    {
        var (sql, parameters) = _tableInfo.GenerateSelectSql(null, WhereClause.Create().Eq("Name", "Hello"));
        var parameterName = parameters.First().Name;

        // TODO: Is there a way to auto detect parameters?
        SqlCompareHelper.SqlEqual($"SELECT * FROM TestEntity WHERE (Name = @{parameterName})", sql);
        Assert.Equal("Hello", parameters.Get<string>(parameterName));
    }
}
