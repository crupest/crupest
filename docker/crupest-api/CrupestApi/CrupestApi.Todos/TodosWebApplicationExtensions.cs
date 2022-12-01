using System;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace CrupestApi.Todos;

public static class TodosWebApplicationExtensions
{
    public static WebApplication MapTodos(this WebApplication app, string path)
    {
        if (app is null)
        {
            throw new ArgumentNullException(nameof(app));
        }

        app.MapGet(path, async ([FromServices] TodosService todosService) =>
        {
            var jsonOptions = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            };

            try
            {
                var todos = await todosService.GetTodosAsync();
                return Results.Json(todos, jsonOptions, statusCode: 200);
            }
            catch (Exception e)
            {
                return Results.Json(new
                {
                    e.Message
                }, jsonOptions, statusCode: StatusCodes.Status503ServiceUnavailable);
            }
        });

        return app;
    }
}