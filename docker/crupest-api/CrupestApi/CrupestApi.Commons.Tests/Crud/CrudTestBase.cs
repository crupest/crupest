using Microsoft.AspNetCore.TestHost;

namespace CrupestApi.Commons.Crud.Tests;

public abstract class CrudTestBase : IAsyncDisposable
{
    protected readonly WebApplication _app;

    protected readonly string _path;
    protected readonly string? _authKey;

    protected readonly HttpClient _client;

    public CrudTestBase(string path, string? authKey = null)
    {
        _path = path;
        _authKey = authKey;

        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder.Services.AddCrudCore();
        ConfigureApplication(builder);
        _app = builder.Build();

        _client = CreateHttpClient();
    }

    protected abstract void ConfigureApplication(WebApplicationBuilder builder);

    public virtual async ValueTask DisposeAsync()
    {
        await _app.DisposeAsync();
    }

    public TestServer GetTestServer()
    {
        return _app.GetTestServer();
    }

    public HttpClient CreateHttpClient()
    {
        return GetTestServer().CreateClient();
    }
}
