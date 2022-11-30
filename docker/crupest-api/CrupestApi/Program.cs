using System;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.DependencyInjection;
using CrupestApi.Config;
using CrupestApi.Services;

namespace CrupestApi
{
    internal class Program
    {
        private static void Main(string[] args)
        {

            var builder = WebApplication.CreateBuilder(args);

            string configFilePath = Environment.GetEnvironmentVariable("CRUPEST_API_CONFIG_FILE") ?? "/crupest-api-config.json";
            builder.Configuration.AddJsonFile(configFilePath, optional: false, reloadOnChange: true);

            builder.Services.AddOptions<TodoConfiguration>();
            builder.Services.Configure<TodoConfiguration>(builder.Configuration.GetSection("Todos"));
            builder.Services.PostConfigure<TodoConfiguration>(config =>
            {
                if (config.Count is null)
                {
                    config.Count = 20;
                }
            });
            builder.Services.TryAddScoped<TodoService>();

            var app = builder.Build();

            app.MapGet("/api/todos", async ([FromServices] TodoService todoService) =>
            {
                try
                {
                    var todos = await todoService.GetTodosAsync();
                    return Results.Json(todos, new JsonSerializerOptions
                    {
                        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
                    }, statusCode: 200);
                }
                catch (Exception e)
                {
                    return Results.Json(new
                    {
                        e.Message
                    }, statusCode: StatusCodes.Status503ServiceUnavailable);
                }
            });

            app.Run();
        }
    }
}
