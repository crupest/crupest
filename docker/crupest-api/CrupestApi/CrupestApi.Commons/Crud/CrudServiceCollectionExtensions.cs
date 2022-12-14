using Microsoft.Extensions.DependencyInjection.Extensions;

namespace CrupestApi.Commons.Crud;

public static class CrudServiceCollectionExtensions
{
    public static IServiceCollection AddCrudCore(this IServiceCollection services)
    {
        services.TryAddSingleton<IDbConnectionFactory, SqliteConnectionFactory>();
        services.TryAddSingleton<IColumnTypeProvider, ColumnTypeProvider>();
        services.TryAddSingleton<ITableInfoFactory, TableInfoFactory>();
        return services;
    }

    public static IServiceCollection AddCrud<TEntity>(this IServiceCollection services) where TEntity : class
    {
        AddCrudCore(services);

        services.TryAddScoped<CrudService<TEntity>>();
        services.TryAddScoped<EntityJsonHelper<TEntity>>();

        return services;
    }
}
