using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Mime;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Microsoft.AspNetCore.Http;
using CrupestApi.Config;

namespace CrupestApi
{
    public class TodoItem
    {
        public string Status { get; set; } = default!;
        public string Title { get; set; } = default!;
        public bool Closed { get; set; }
        public string color { get; set; } = default!;
    }

    internal class Program
    {
        private static void Main(string[] args)
        {
            using var httpClient = new HttpClient();

            var builder = WebApplication.CreateBuilder(args);

            string configFilePath = Environment.GetEnvironmentVariable("CRUPEST_API_CONFIG_FILE") ?? "/config.json";

            builder.Configuration.AddJsonFile(configFilePath, optional: false, reloadOnChange: true);

            var app = builder.Build();

            app.MapGet("/api/todos", async ([FromServices] IConfiguration configuration, [FromServices] ILoggerFactory loggerFactory) =>
            {
                var logger = loggerFactory.CreateLogger("CrupestApi.Todos");

                static string CreateGraphQLQuery(TodoConfiguration todoConfiguration)
                {
                    return $$"""
{
    user(login: "{{todoConfiguration.Username}}") {
        projectV2(number: {{todoConfiguration.ProjectNumber}}) {
          items(last: {{todoConfiguration.Count ?? 20}}) {
            nodes {
              __typename
              content {
                __typename
                ... on Issue {
                  title
                  closed
                }
                ... on PullRequest {
                  title
                  closed
                }
                ... on DraftIssue {
                  title
                }
              }
            }
          }
        }
      }
    }
""";
                }

                var todoConfiguration = configuration.GetSection("Todos").Get<TodoConfiguration>();
                if (todoConfiguration is null)
                {
                    throw new Exception("Fail to get todos configuration.");
                }

                using var requestContent = new StringContent(JsonSerializer.Serialize(new
                {
                    query = CreateGraphQLQuery(todoConfiguration)
                }));
                requestContent.Headers.ContentType = new MediaTypeHeaderValue(MediaTypeNames.Application.Json, Encoding.UTF8.WebName);

                using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.github.com/graphql");
                request.Content = requestContent;
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", todoConfiguration.Token);
                request.Headers.TryAddWithoutValidation("User-Agent", "crupest");

                using var response = await httpClient.SendAsync(request);
                var responseBody = await response.Content.ReadAsStringAsync();
                logger.LogInformation(response.StatusCode.ToString());
                logger.LogInformation(responseBody);


                if (response.IsSuccessStatusCode)
                {
                    using var responseJson = JsonSerializer.Deserialize<JsonDocument>(responseBody);
                    if (responseJson is null)
                    {
                        throw new Exception("Fail to deserialize response body.");
                    }

                    var nodes = responseJson.RootElement.GetProperty("data").GetProperty("user").GetProperty("projectV2").GetProperty("items").GetProperty("nodes").EnumerateArray();

                    var result = new List<TodoItem>();

                    foreach (var node in nodes)
                    {
                        var content = node.GetProperty("content");
                        var title = content.GetProperty("title").GetString();
                        if (title is null)
                        {
                            throw new Exception("Fail to get title.");
                        }
                        JsonElement closedElement;
                        bool closed;
                        if (content.TryGetProperty("closed", out closedElement))
                        {
                            closed = closedElement.GetBoolean();
                        }
                        else
                        {
                            closed = false;
                        }

                        result.Add(new TodoItem
                        {
                            Title = title,
                            Status = closed ? "Done" : "Todo",
                            Closed = closed,
                            color = closed ? "green" : "blue"
                        });
                    }

                    return Results.Json(result, new JsonSerializerOptions
                    {
                        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
                    }, statusCode: 200);
                }
                else
                {
                    const string message = "Fail to get todos from GitHub.";
                    logger.LogError(message);

                    return Results.Json(new
                    {
                        message
                    }, statusCode: StatusCodes.Status503ServiceUnavailable);
                }
            });

            app.Run();
        }
    }
}
