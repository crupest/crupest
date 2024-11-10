using CrupestApi.Commons;

namespace CrupestApi.Todos;

public static class TodosWebApplicationExtensions
{
    public static WebApplication MapTodos(this WebApplication app, string path)
    {
        if (app is null)
        {
            throw new ArgumentNullException(nameof(app));
        }

        app.MapGet(path, async (context) =>
        {
            var todosService = context.RequestServices.GetRequiredService<TodosService>();

            try
            {
                var todos = await todosService.GetTodosAsync();
                await context.Response.WriteJsonAsync(todos);

            }
            catch (Exception e)
            {
                await context.Response.WriteMessageAsync(e.Message, statusCode: StatusCodes.Status503ServiceUnavailable);
            }
        });

        return app;
    }
}