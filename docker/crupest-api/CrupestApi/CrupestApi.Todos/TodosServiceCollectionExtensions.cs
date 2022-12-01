using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace CrupestApi.Todos;

public static class TodosServiceCollectionExtensions
{
    public static IServiceCollection AddTodos(this IServiceCollection services)
    {
        services.AddOptions<TodosConfiguration>().BindConfiguration("Todos");
        services.PostConfigure<TodosConfiguration>(config =>
        {
            if (config.Count == 0)
            {
                config.Count = 20;
            }
        });
        services.TryAddScoped<TodosService>();
        return services;
    }
}

