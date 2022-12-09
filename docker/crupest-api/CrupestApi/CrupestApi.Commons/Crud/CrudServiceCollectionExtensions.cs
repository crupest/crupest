using Microsoft.Extensions.DependencyInjection.Extensions;

namespace CrupestApi.Commons.Crud;

public static class CrudServiceCollectionExtensions
{
    public static IServiceCollection UseCrud(this IServiceCollection services)
    {
        services.TryAddSingleton<IDbConnectionFactory, SqliteConnectionFactory>();
        services.TryAddSingleton<IColumnTypeProvider, ColumnTypeProvider>();
        services.TryAddSingleton<ITableInfoFactory, TableInfoFactory>();
        return services;
    }
}
