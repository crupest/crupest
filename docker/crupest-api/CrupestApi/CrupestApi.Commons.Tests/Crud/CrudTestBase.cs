using System.Net;
using CrupestApi.Commons.Secrets;
using Microsoft.AspNetCore.TestHost;

namespace CrupestApi.Commons.Crud.Tests;

public abstract class CrudTestBase<TEntity> : IAsyncDisposable where TEntity : class
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
        builder.Services.AddCrud<TEntity>();
        ConfigureApplication(builder);
        _app = builder.Build();

        if (authKey is not null)
        {
            using (var scope = _app.Services.CreateScope())
            {
                var secretService = scope.ServiceProvider.GetRequiredService<ISecretService>();
                secretService.CreateTestSecret(authKey, "test-secret");
            }
        }

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

    public async Task TestAuth()
    {
        if (_authKey is null)
        {
            return;
        }

        {
            using var response = await _client.GetAsync(_path);
            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        }

        {
            var entity = Activator.CreateInstance<TEntity>();
            using var response = await _client.PostAsJsonAsync(_path, entity);
            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        }
    }
}
