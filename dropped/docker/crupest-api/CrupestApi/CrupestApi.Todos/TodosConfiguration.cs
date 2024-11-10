using System.ComponentModel.DataAnnotations;

namespace CrupestApi.Todos;

public class TodosConfiguration
{
    [Required]
    public string Username { get; set; } = default!;
    [Required]
    public int ProjectNumber { get; set; } = default!;
    [Required]
    public string Token { get; set; } = default!;
    public int Count { get; set; }
}