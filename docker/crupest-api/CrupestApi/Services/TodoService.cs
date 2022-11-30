using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Mime;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using CrupestApi.Config;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace CrupestApi.Services
{
    public class TodoItem
    {
        public string Status { get; set; } = default!;
        public string Title { get; set; } = default!;
        public bool Closed { get; set; }
        public string color { get; set; } = default!;
    }

    public class TodoService
    {
        private readonly IOptionsSnapshot<TodoConfiguration> _options;
        private readonly ILogger<TodoService> _logger;

        public TodoService(IOptionsSnapshot<TodoConfiguration> options, ILogger<TodoService> logger)
        {
            _options = options;
            _logger = logger;
        }

        private static string CreateGraphQLQuery(TodoConfiguration todoConfiguration)
        {
            return $$"""
{
    user(login: "{{todoConfiguration.Username}}") {
        projectV2(number: {{todoConfiguration.ProjectNumber}}) {
            items(last: {{todoConfiguration.Count}}) {
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


        public async Task<List<TodoItem>> GetTodosAsync()
        {
            var todoOptions = _options.Value;
            if (todoOptions is null)
            {
                throw new Exception("Fail to get todos configuration.");
            }

            _logger.LogInformation("Username: {}; ProjectNumber: {}; Count: {}", todoOptions.Username, todoOptions.ProjectNumber, todoOptions.Count);
            _logger.LogInformation("Getting todos from GitHub GraphQL API...");

            using var httpClient = new HttpClient();

            using var requestContent = new StringContent(JsonSerializer.Serialize(new
            {
                query = CreateGraphQLQuery(todoOptions)
            }));
            requestContent.Headers.ContentType = new MediaTypeHeaderValue(MediaTypeNames.Application.Json, Encoding.UTF8.WebName);

            using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.github.com/graphql");
            request.Content = requestContent;
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", todoOptions.Token);
            request.Headers.TryAddWithoutValidation("User-Agent", todoOptions.Username);

            using var response = await httpClient.SendAsync(request);
            var responseBody = await response.Content.ReadAsStringAsync();

            _logger.LogInformation("GitHub server returned status code: {}", response.StatusCode);
            _logger.LogInformation("GitHub server returned body: {}", responseBody);

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

                return result;
            }
            else
            {
                const string message = "Fail to get todos from GitHub.";
                _logger.LogError(message);
                throw new Exception(message);
            }
        }
    }
}