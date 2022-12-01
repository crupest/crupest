using System;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.Configuration;
using CrupestApi.Todos;

var builder = WebApplication.CreateBuilder(args);

string configFilePath = Environment.GetEnvironmentVariable("CRUPEST_API_CONFIG_FILE") ?? "/crupest-api-config.json";
builder.Configuration.AddJsonFile(configFilePath, optional: false, reloadOnChange: true);

builder.Services.AddTodos();

var app = builder.Build();

app.MapTodos("/api/todos");

app.Run();
