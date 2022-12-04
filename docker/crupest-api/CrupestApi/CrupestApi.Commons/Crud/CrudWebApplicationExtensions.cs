namespace CrupestApi.Commons.Crud;

public static class CrudWebApplicationExtensions
{
    public static IApplicationBuilder UseCrud(this IApplicationBuilder app, string path)
    {
        return app;
    }
}
