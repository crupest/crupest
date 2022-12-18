namespace CrupestApi.Commons.Crud;

public static class CrudWebApplicationExtensions
{
    public static WebApplication UseCrud<TEntity>(this WebApplication app, string path, string? key) where TEntity : class
    {
        app.MapGet(path, async (context) =>
        {
            
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var allEntities = crudService.GetAll();
            await context.ResponseJsonAsync(allEntities.Select(e => crudService.JsonHelper.ConvertEntityToDictionary(e)));
        });

        app.MapGet(path + "/{key}", async (context) =>
        {
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var key = context.Request.RouteValues["key"]?.ToString();
            if (key == null)
            {
                await context.ResponseMessageAsync("Please specify a key in path.");
                return;
            }

            var entity = crudService.GetByKey(key);
            await context.ResponseJsonAsync(crudService.JsonHelper.ConvertEntityToDictionary(entity));
        });

        app.MapPost(path, async (context) =>
        {
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var jsonDocument = await context.Request.ReadJsonAsync();
            var key = crudService.Create(jsonDocument.RootElement);
            await context.ResponseJsonAsync(crudService.JsonHelper.ConvertEntityToDictionary(crudService.GetByKey(key)));
        });

        app.MapPatch(path + "/{key}", async (context) =>
        {
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var key = context.Request.RouteValues["key"]?.ToString();
            if (key == null)
            {
                await context.ResponseMessageAsync("Please specify a key in path.");
                return;
            }

            var jsonDocument = await context.Request.ReadJsonAsync();
            crudService.UpdateByKey(key, jsonDocument.RootElement);

            await context.ResponseJsonAsync(crudService.JsonHelper.ConvertEntityToDictionary(crudService.GetByKey(key)));
        });

        app.MapDelete(path + "/{key}", async (context) =>
        {
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var key = context.Request.RouteValues["key"]?.ToString();
            if (key == null)
            {
                await context.ResponseMessageAsync("Please specify a key in path.");
                return;
            }

            crudService.DeleteByKey(key);
            await context.ResponseMessageAsync("Deleted.", StatusCodes.Status200OK);
        });

        return app;
    }
}
