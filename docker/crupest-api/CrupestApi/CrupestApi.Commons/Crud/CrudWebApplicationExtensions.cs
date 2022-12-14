namespace CrupestApi.Commons.Crud;

public static class CrudWebApplicationExtensions
{
    public static WebApplication UseCrud<TEntity>(this WebApplication app, string path) where TEntity : class
    {
        app.MapGet(path, async (context) =>
        {
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var entityJsonHelper = context.RequestServices.GetRequiredService<EntityJsonHelper<TEntity>>();
            var allEntities = crudService.GetAll();
            await context.ResponseJsonAsync(allEntities.Select(e => entityJsonHelper.ConvertEntityToDictionary(e)));
        });

        app.MapPost(path, async (context) =>
        {
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var entityJsonHelper = context.RequestServices.GetRequiredService<EntityJsonHelper<TEntity>>();
            // TODO: Continue here.
        });

        return app;
    }
}
