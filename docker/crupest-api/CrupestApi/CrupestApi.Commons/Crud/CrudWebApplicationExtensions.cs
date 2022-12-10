namespace CrupestApi.Commons.Crud;

public static class CrudWebApplicationExtensions
{
    public static WebApplication UseCrud(this WebApplication app, string path)
    {
        app.MapGet(path, async (context) =>
        {

        });

        return app;
    }
}
