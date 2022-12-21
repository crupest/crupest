using Microsoft.Extensions.Logging.Abstractions;

namespace CrupestApi.Commons.Crud.Tests;

public class CrudServiceTest
{
    private readonly SqliteMemoryConnectionFactory _memoryConnectionFactory = new SqliteMemoryConnectionFactory();

    private readonly CrudService<TestEntity> _crudService;

    public CrudServiceTest()
    {
        var columnTypeProvider = new ColumnTypeProvider();
        var tableInfoFactory = new TableInfoFactory(columnTypeProvider, NullLoggerFactory.Instance);
        var dbConnectionFactory = new SqliteMemoryConnectionFactory();

        _crudService = new CrudService<TestEntity>(
            tableInfoFactory, dbConnectionFactory, NullLoggerFactory.Instance);
    }

    [Fact]
    public void CrudTest()
    {
        _crudService.Create(new TestEntity()
        {
            Name = "crupest",
            Age = 18,
        });
    }


}
