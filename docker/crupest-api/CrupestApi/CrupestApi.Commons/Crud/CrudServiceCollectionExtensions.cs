using Microsoft.Extensions.DependencyInjection.Extensions;

namespace CrupestApi.Commons.Crud;

public static class CrudServiceCollectionExtensions
{
    public static IServiceCollection UseCrud(this IServiceCollection services)
    {
        services.TryAddSingleton<IColumnTypeProvider, ColumnTypeProvider>();
        return services;
    }
}
