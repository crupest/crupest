using System.Data;

namespace CrupestApi.Commons.Crud;

// TODO: Implement and register this service.
public interface IDbConnectionFactory
{
    IDbConnection Get(string? name = null);
}
