using Dapper;

namespace CrupestApi.Commons.Crud;

public interface IClause
{
    IEnumerable<IClause> GetSubclauses()
    {
        return Enumerable.Empty<IClause>();
    }

    IEnumerable<string> GetRelatedColumns()
    {
        var subclauses = GetSubclauses();
        var result = new List<string>();
        foreach (var subclause in subclauses)
        {
            var columns = subclause.GetRelatedColumns();
            if (columns is not null)
                result.AddRange(columns);
        }
        return result;
    }
}
