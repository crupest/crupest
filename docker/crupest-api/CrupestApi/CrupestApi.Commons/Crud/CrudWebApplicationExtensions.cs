namespace CrupestApi.Commons.Crud;

public static class CrudWebApplicationExtensions
{
    public static WebApplication UseCrud<TEntity>(this WebApplication app, string path) where TEntity : class
    {
        app.MapGet(path, async (context) =>
        {
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var result = crudService.SelectAsJson(null);
            await context.ResponseJsonAsync(result);
        });

        app.MapPost(path, async (context) =>
        {
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();

        });

        return app;
    }
}
