using System.ComponentModel.DataAnnotations;

namespace CrupestApi.Config
{
    public class TodoConfiguration
    {
        [Required]
        public string Username { get; set; } = default!;
        [Required]
        public int ProjectNumber { get; set; } = default!;
        [Required]
        public string Token { get; set; } = default!;
        public int? Count { get; set; }
    }
}