namespace CrupestApi.Commons.Crud;

public static class CrudWebApplicationExtensions
{
    public static WebApplication MapCrud<TEntity>(this WebApplication app, string path, string? permission) where TEntity : class
    {
        app.MapGet(path, async (context) =>
        {
            if (!context.RequirePermission(permission)) return;
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var entityJsonHelper = context.RequestServices.GetRequiredService<EntityJsonHelper<TEntity>>();
            var allEntities = crudService.GetAll();
            await context.ResponseJsonAsync(allEntities.Select(e => entityJsonHelper.ConvertEntityToDictionary(e)));
        });

        app.MapGet(path + "/{key}", async (context) =>
        {
            if (!context.RequirePermission(permission)) return;
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var entityJsonHelper = context.RequestServices.GetRequiredService<EntityJsonHelper<TEntity>>();
            var key = context.Request.RouteValues["key"]?.ToString();
            if (key == null)
            {
                await context.ResponseMessageAsync("Please specify a key in path.");
                return;
            }

            var entity = crudService.GetByKey(key);
            await context.ResponseJsonAsync(entityJsonHelper.ConvertEntityToDictionary(entity));
        });

        app.MapPost(path, async (context) =>
        {
            if (!context.RequirePermission(permission)) return;
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var entityJsonHelper = context.RequestServices.GetRequiredService<EntityJsonHelper<TEntity>>();
            var jsonDocument = await context.Request.ReadJsonAsync();
            var key = crudService.Create(entityJsonHelper.ConvertJsonToEntityForInsert(jsonDocument.RootElement));
            await context.ResponseJsonAsync(entityJsonHelper.ConvertEntityToDictionary(crudService.GetByKey(key)));
        });

        app.MapPatch(path + "/{key}", async (context) =>
        {
            if (!context.RequirePermission(permission)) return;
            var key = context.Request.RouteValues["key"]?.ToString();
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var entityJsonHelper = context.RequestServices.GetRequiredService<EntityJsonHelper<TEntity>>();
            if (key == null)
            {
                await context.ResponseMessageAsync("Please specify a key in path.");
                return;
            }

            var jsonDocument = await context.Request.ReadJsonAsync();
            var entity = entityJsonHelper.ConvertJsonToEntityForUpdate(jsonDocument.RootElement, out var updateBehavior);
            var newKey = crudService.UpdateByKey(key, entity, updateBehavior);
            await context.ResponseJsonAsync(entityJsonHelper.ConvertEntityToDictionary(crudService.GetByKey(newKey)));
        });

        app.MapDelete(path + "/{key}", async (context) =>
        {
            if (!context.RequirePermission(permission)) return;
            var crudService = context.RequestServices.GetRequiredService<CrudService<TEntity>>();
            var key = context.Request.RouteValues["key"]?.ToString();
            if (key == null)
            {
                await context.ResponseMessageAsync("Please specify a key in path.");
                return;
            }

            var deleted = crudService.DeleteByKey(key);
            if (deleted)
                await context.ResponseMessageAsync("Deleted.", StatusCodes.Status200OK);
            else
                await context.ResponseMessageAsync("Not exist.", StatusCodes.Status200OK);
        });

        return app;
    }
}
