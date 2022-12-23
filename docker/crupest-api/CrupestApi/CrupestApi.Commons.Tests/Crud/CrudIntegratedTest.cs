using System.Net;
using System.Net.Http.Headers;
using CrupestApi.Commons.Secrets;
using Microsoft.AspNetCore.TestHost;

namespace CrupestApi.Commons.Crud.Tests;

public class CrudIntegratedTest : IAsyncLifetime
{
    private readonly WebApplication _app;
    private HttpClient _httpClient = default!;
    private HttpClient _authorizedHttpClient = default!;
    private string _token = default!;

    public CrudIntegratedTest()
    {
        var builder = WebApplication.CreateBuilder();
        builder.Logging.ClearProviders();
        builder.Services.AddSingleton<IDbConnectionFactory, SqliteMemoryConnectionFactory>();
        builder.Services.AddCrud<TestEntity>();
        builder.WebHost.UseTestServer();
        _app = builder.Build();
        _app.MapCrud<TestEntity>("/test", "test-perm");
    }

    public async Task InitializeAsync()
    {
        await _app.StartAsync();
        _httpClient = _app.GetTestClient();

        using (var scope = _app.Services.CreateScope())
        {
            var secretService = (SecretService)scope.ServiceProvider.GetRequiredService<ISecretService>();
            var key = secretService.Create(new SecretInfo
            {
                Key = "test-perm"
            });
            _token = secretService.GetByKey(key).Secret;
        }

        _authorizedHttpClient = _app.GetTestClient();
        _authorizedHttpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", _token);
    }

    public async Task DisposeAsync()
    {
        await _app.StopAsync();
    }


    [Fact]
    public async Task EmptyTest()
    {
        using var response = await _authorizedHttpClient.GetAsync("/test");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadFromJsonAsync<List<TestEntity>>();
        Assert.NotNull(body);
        Assert.Empty(body);
    }

    [Fact]
    public async Task CrudTest()
    {
        {
            using var response = await _authorizedHttpClient.PostAsJsonAsync("/test", new TestEntity
            {
                Name = "test",
                Age = 22
            });
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var body = await response.Content.ReadFromJsonAsync<TestEntity>();
            Assert.NotNull(body);
            Assert.Equal("test", body.Name);
            Assert.Equal(22, body.Age);
            Assert.Null(body.Height);
            Assert.NotEmpty(body.Secret);
        }

        {
            using var response = await _authorizedHttpClient.GetAsync("/test");
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var body = await response.Content.ReadFromJsonAsync<List<TestEntity>>();
            Assert.NotNull(body);
            var entity = Assert.Single(body);
            Assert.Equal("test", entity.Name);
            Assert.Equal(22, entity.Age);
            Assert.Null(entity.Height);
            Assert.NotEmpty(entity.Secret);
        }

        {
            using var response = await _authorizedHttpClient.GetAsync("/test/test");
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var body = await response.Content.ReadFromJsonAsync<TestEntity>();
            Assert.NotNull(body);
            Assert.Equal("test", body.Name);
            Assert.Equal(22, body.Age);
            Assert.Null(body.Height);
            Assert.NotEmpty(body.Secret);
        }

        {
            using var response = await _authorizedHttpClient.PatchAsJsonAsync("/test/test", new TestEntity
            {
                Name = "test-2",
                Age = 23,
                Height = 188.0f
            });
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var body = await response.Content.ReadFromJsonAsync<TestEntity>();
            Assert.NotNull(body);
            Assert.Equal("test-2", body.Name);
            Assert.Equal(23, body.Age);
            Assert.Equal(188.0f, body.Height);
            Assert.NotEmpty(body.Secret);
        }

        {
            using var response = await _authorizedHttpClient.GetAsync("/test/test-2");
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var body = await response.Content.ReadFromJsonAsync<TestEntity>();
            Assert.NotNull(body);
            Assert.Equal("test-2", body.Name);
            Assert.Equal(23, body.Age);
            Assert.Equal(188.0f, body.Height);
            Assert.NotEmpty(body.Secret);
        }

        {
            using var response = await _authorizedHttpClient.DeleteAsync("/test/test-2");
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        }

        {
            using var response = await _authorizedHttpClient.GetAsync("/test");
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var body = await response.Content.ReadFromJsonAsync<List<TestEntity>>();
            Assert.NotNull(body);
            Assert.Empty(body);
        }
    }
}
