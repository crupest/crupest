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
        builder.Services.AddSingleton<SqliteMemoryConnectionFactory>();
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
    public async Task Test()
    {
        var response = await _authorizedHttpClient.GetAsync($"/test?secret={_token}");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadFromJsonAsync<List<TestEntity>>();
        Assert.NotNull(body);
        Assert.Empty(body);
    }
}
