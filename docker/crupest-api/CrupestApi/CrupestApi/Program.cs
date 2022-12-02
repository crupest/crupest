using CrupestApi.Commons;
using CrupestApi.Secrets;
using CrupestApi.Todos;

var builder = WebApplication.CreateBuilder(args);

string configFilePath = Environment.GetEnvironmentVariable("CRUPEST_API_CONFIG_FILE") ?? "/crupest-api-config.json";
builder.Configuration.AddJsonFile(configFilePath, optional: false, reloadOnChange: true);

builder.Services.AddJsonOptions();
builder.Services.AddTodos();

var app = builder.Build();

app.MapTodos("/api/todos");
app.MapSecrets("/api/secrets");

app.Run();
