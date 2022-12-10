using Xunit.Abstractions;

namespace CrupestApi.Commons.Crud.Tests;

public class TableInfoTest
{
    private static TableInfoFactory TableInfoFactory = new TableInfoFactory(new ColumnTypeProvider());

    private TableInfo _tableInfo;

    public TableInfoTest()
    {
        _tableInfo = TableInfoFactory.Get(typeof(TestEntity));
    }

    [Fact]
    public void TestColumnCount()
    {
        Assert.Equal(4, _tableInfo.ColumnInfos.Count);
        Assert.Equal(3, _tableInfo.ColumnProperties.Count);
        Assert.Equal(1, _tableInfo.NonColumnProperties.Count);
    }

    [Fact]
    public void GenerateSelectSqlTest()
    {
        var (sql, parameters) = _tableInfo.GenerateSelectSql(null, WhereClause.Create().Eq("Name", "Hello"));
        var parameterName = parameters.ParameterNames.First();

        // TODO: Is there a way to auto detect parameters?
        SqlCompareHelper.SqlEqual($"SELECT * FROM TestEntity WHERE (Name = @{parameterName})", sql);
        Assert.Equal("Hello", parameters.Get<string>(parameterName));
    }
}
