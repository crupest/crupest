using System.Diagnostics;
using Dapper;

namespace CrupestApi.Commons.Crud;

public interface IWhereClause
{
    string GenerateSql(DynamicParameters parameters);

    IEnumerable<IWhereClause>? GetSubclauses()
    {
        return null;
    }

    IEnumerable<string>? GetRelatedColumns()
    {
        var subclauses = GetSubclauses();
        if (subclauses is null) return null;
        var result = new List<string>();
        foreach (var subclause in subclauses)
        {
            var columns = subclause.GetRelatedColumns();
            if (columns is not null)
                result.AddRange(columns);
        }
        return result;
    }

    public static string RandomKey(int length)
    {
        // I think it's safe to use random here because it's just to differentiate the parameters.
        // TODO: Consider data race!
        var random = new Random();
        var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        var result = new string(Enumerable.Repeat(chars, length)
            .Select(s => s[random.Next(s.Length)]).ToArray());
        return result;
    }

    public static string GenerateRandomParameterName(DynamicParameters parameters)
    {
        var parameterName = IWhereClause.RandomKey(10);
        int retryTimes = 1;
        while (parameters.ParameterNames.Contains(parameterName))
        {
            retryTimes++;
            Debug.Assert(retryTimes <= 100);
            parameterName = IWhereClause.RandomKey(10);
        }
        return parameterName;
    }
}

public static class DynamicParametersExtensions
{
    public static string AddRandomNameParameter(this DynamicParameters parameters, object value)
    {
        var parameterName = IWhereClause.GenerateRandomParameterName(parameters);
        parameters.Add(parameterName, value);
        return parameterName;
    }
}

public class AndWhereClause : IWhereClause
{
    public List<IWhereClause> Clauses { get; } = new List<IWhereClause>();

    public IEnumerable<IWhereClause> GetSubclauses()
    {
        return Clauses;
    }

    public AndWhereClause(IEnumerable<IWhereClause> clauses)
    {
        Clauses.AddRange(clauses);
    }

    public AndWhereClause(params IWhereClause[] clauses)
    {
        Clauses.AddRange(clauses);
    }

    public static AndWhereClause Create(params IWhereClause[] clauses)
    {
        return new AndWhereClause(clauses);
    }

    public string GenerateSql(DynamicParameters parameters)
    {
        return string.Join(" AND ", Clauses.Select(c => $"({c.GenerateSql(parameters)})"));
    }
}

public class OrWhereClause : IWhereClause
{
    public List<IWhereClause> Clauses { get; } = new List<IWhereClause>();

    public IEnumerable<IWhereClause> GetSubclauses()
    {
        return Clauses;
    }

    public OrWhereClause(IEnumerable<IWhereClause> clauses)
    {
        Clauses.AddRange(clauses);
    }

    public OrWhereClause(params IWhereClause[] clauses)
    {
        Clauses.AddRange(clauses);
    }

    public static OrWhereClause Create(params IWhereClause[] clauses)
    {
        return new OrWhereClause(clauses);
    }

    public string GenerateSql(DynamicParameters parameters)
    {
        return string.Join(" OR ", Clauses.Select(c => $"({c.GenerateSql(parameters)})"));
    }
}

public class CompareWhereClause : IWhereClause
{
    public string Column { get; }
    public string Operator { get; }
    public object Value { get; }

    public List<string> GetRelatedColumns()
    {
        return new List<string> { Column };
    }

    // It's user's responsibility to keep column safe, with proper escape.
    public CompareWhereClause(string column, string @operator, object value)
    {
        Column = column;
        Operator = @operator;
        Value = value;
    }

    public static CompareWhereClause Create(string column, string @operator, object value)
    {
        return new CompareWhereClause(column, @operator, value);
    }

    public static CompareWhereClause Eq(string column, object value)
    {
        return new CompareWhereClause(column, "=", value);
    }

    public static CompareWhereClause Neq(string column, object value)
    {
        return new CompareWhereClause(column, "<>", value);
    }

    public static CompareWhereClause Gt(string column, object value)
    {
        return new CompareWhereClause(column, ">", value);
    }

    public static CompareWhereClause Gte(string column, object value)
    {
        return new CompareWhereClause(column, ">=", value);
    }

    public static CompareWhereClause Lt(string column, object value)
    {
        return new CompareWhereClause(column, "<", value);
    }

    public static CompareWhereClause Lte(string column, object value)
    {
        return new CompareWhereClause(column, "<=", value);
    }

    public string GenerateSql(DynamicParameters parameters)
    {
        var parameterName = parameters.AddRandomNameParameter(Value);
        return $"{Column} {Operator} @{parameterName}";
    }
}

public class WhereClause : IWhereClause
{
    public DynamicParameters Parameters { get; } = new DynamicParameters();
    public List<IWhereClause> Clauses { get; } = new List<IWhereClause>();

    public WhereClause(IEnumerable<IWhereClause> clauses)
    {
        Clauses.AddRange(clauses);
    }

    public WhereClause(params IWhereClause[] clauses)
    {
        Clauses.AddRange(clauses);
    }

    public IEnumerable<IWhereClause> GetSubclauses()
    {
        return Clauses;
    }

    public WhereClause Add(params IWhereClause[] clauses)
    {
        Clauses.AddRange(clauses);
        return this;
    }

    public static WhereClause Create(params IWhereClause[] clauses)
    {
        return new WhereClause(clauses);
    }

    public WhereClause Eq(string column, object value)
    {
        return Add(CompareWhereClause.Eq(column, value));
    }

    public WhereClause Neq(string column, object value)
    {
        return Add(CompareWhereClause.Neq(column, value));
    }

    public WhereClause Eq(IEnumerable<KeyValuePair<string, object>> columnValueMap)
    {
        var clauses = columnValueMap.Select(kv => (IWhereClause)CompareWhereClause.Eq(kv.Key, kv.Value)).ToArray();
        return Add(clauses);
    }

    public string GenerateSql(DynamicParameters dynamicParameters)
    {
        return string.Join(" AND ", Clauses.Select(c => $"({c.GenerateSql(Parameters)})"));
    }

    public string GenerateSql()
    {
        return GenerateSql(Parameters);
    }
}
