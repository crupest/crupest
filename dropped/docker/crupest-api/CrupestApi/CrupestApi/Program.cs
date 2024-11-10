using CrupestApi.Commons;
using CrupestApi.Commons.Crud;
using CrupestApi.Secrets;
using CrupestApi.Todos;

var builder = WebApplication.CreateBuilder(args);

string configFilePath = Environment.GetEnvironmentVariable("CRUPEST_API_CONFIG_FILE") ?? "/crupest-api-config.json";
builder.Configuration.AddJsonFile(configFilePath, optional: false, reloadOnChange: true);

builder.Services.AddJsonOptions();
builder.Services.AddCrupestApiConfig();

builder.Services.AddTodos();
builder.Services.AddSecrets();

var app = builder.Build();

app.UseCrudCore();
app.MapTodos("/api/todos");
// TODO: It's not safe now!
// app.MapSecrets("/api/secrets");

app.Run();
