using CrupestApi.Commons.Crud.Migrations;
using CrupestApi.Commons.Secrets;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace CrupestApi.Commons.Crud;

public static class CrudServiceCollectionExtensions
{
    public static IServiceCollection AddCrudCore(this IServiceCollection services)
    {
        services.TryAddSingleton<IDbConnectionFactory, SqliteConnectionFactory>();
        services.TryAddSingleton<IColumnTypeProvider, ColumnTypeProvider>();
        services.TryAddSingleton<ITableInfoFactory, TableInfoFactory>();
        services.TryAddSingleton<IDatabaseMigrator, SqliteDatabaseMigrator>();
        services.AddSecrets();
        return services;
    }

    public static IServiceCollection AddCrud<TEntity, TCrudService>(this IServiceCollection services) where TEntity : class where TCrudService : CrudService<TEntity>
    {
        AddCrudCore(services);

        services.TryAddScoped<CrudService<TEntity>, TCrudService>();
        services.TryAddScoped<EntityJsonHelper<TEntity>>();

        return services;
    }

    public static IServiceCollection AddCrud<TEntity>(this IServiceCollection services) where TEntity : class
    {
        return services.AddCrud<TEntity, CrudService<TEntity>>();
    }

}
