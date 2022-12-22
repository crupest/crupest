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
        var key = _crudService.Create(new TestEntity()
        {
            Name = "crupest",
            Age = 18,
        });

        Assert.Equal("crupest", key);

        var entity = _crudService.GetByKey(key);
        Assert.Equal("crupest", entity.Name);
        Assert.Equal(18, entity.Age);
        Assert.Null(entity.Height);
        Assert.NotEmpty(entity.Secret);

        var list = _crudService.GetAll();
        entity = Assert.Single(list);
        Assert.Equal("crupest", entity.Name);
        Assert.Equal(18, entity.Age);
        Assert.Null(entity.Height);
        Assert.NotEmpty(entity.Secret);

        var count = _crudService.GetCount();
        Assert.Equal(1, count);

        _crudService.UpdateByKey(key, new TestEntity()
        {
            Name = "crupest2.0",
            Age = 22,
            Height = 180,
        });

        entity = _crudService.GetByKey("crupest2.0");
        Assert.Equal("crupest2.0", entity.Name);
        Assert.Equal(22, entity.Age);
        Assert.Equal(180, entity.Height);
        Assert.NotEmpty(entity.Secret);

        _crudService.DeleteByKey("crupest2.0");

        count = _crudService.GetCount();
        Assert.Equal(0, count);
    }

    [Fact]
    public void EntityNotExistTest()
    {
        Assert.Throws<EntityNotExistException>(() => _crudService.GetByKey("KeyNotExist"));
        Assert.Throws<EntityNotExistException>(() => _crudService.UpdateByKey("KeyNotExist", new TestEntity
        {
            Name = "crupest"
        }));
    }
}
