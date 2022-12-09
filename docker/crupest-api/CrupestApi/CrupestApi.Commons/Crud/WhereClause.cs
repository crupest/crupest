using System.Data;
using System.Text;
using Dapper;

namespace CrupestApi.Commons.Crud;

public interface IWhereClause : IClause
{
    (string sql, DynamicParameters parameters) GenerateSql(string? dbProviderId = null);
}

public class CompositeWhereClause : IWhereClause
{
    public CompositeWhereClause(string concatOp, bool parenthesesSubclause, params IWhereClause[] subclauses)
    {
        ConcatOp = concatOp;
        ParenthesesSubclause = parenthesesSubclause;
        Subclauses = subclauses.ToList();
    }

    public string ConcatOp { get; }
    public bool ParenthesesSubclause { get; }
    public List<IWhereClause> Subclauses { get; }

    public (string sql, DynamicParameters parameters) GenerateSql(string? dbProviderId = null)
    {
        var parameters = new DynamicParameters();
        var sql = new StringBuilder();
        var subclauses = GetSubclauses();
        if (subclauses is null) return ("", parameters);
        var first = true;
        foreach (var subclause in Subclauses)
        {
            var (subSql, subParameters) = subclause.GenerateSql(dbProviderId);
            if (subSql is null) continue;
            if (first)
            {
                first = false;
            }
            else
            {
                sql.Append($" {ConcatOp} ");
            }
            if (ParenthesesSubclause)
            {
                sql.Append("(");
            }
            sql.Append(subSql);
            if (ParenthesesSubclause)
            {
                sql.Append(")");
            }
            parameters.AddDynamicParams(subParameters);
        }
        return (sql.ToString(), parameters);
    }

    public object GetSubclauses()
    {
        return Subclauses;
    }
}

public class AndWhereClause : CompositeWhereClause
{
    public AndWhereClause(params IWhereClause[] clauses)
    : this(true, clauses)
    {

    }

    public AndWhereClause(bool parenthesesSubclause, params IWhereClause[] clauses)
    : base("AND", parenthesesSubclause, clauses)
    {

    }

    public static AndWhereClause Create(params IWhereClause[] clauses)
    {
        return new AndWhereClause(clauses);
    }
}

public class OrWhereClause : CompositeWhereClause
{
    public OrWhereClause(params IWhereClause[] clauses)
        : this(true, clauses)
    {

    }

    public OrWhereClause(bool parenthesesSubclause, params IWhereClause[] clauses)
        : base("OR", parenthesesSubclause, clauses)
    {

    }

    public static OrWhereClause Create(params IWhereClause[] clauses)
    {
        return new OrWhereClause(clauses);
    }
}

// It's simple because it only compare column and value but not expressions.
public class SimpleCompareWhereClause : IWhereClause
{
    public string Column { get; }
    public string Operator { get; }
    public object? Value { get; }

    public List<string> GetRelatedColumns()
    {
        return new List<string> { Column };
    }

    // It's user's responsibility to keep column safe, with proper escape.
    public SimpleCompareWhereClause(string column, string op, object? value)
    {
        Column = column;
        Operator = op;
        Value = value;
    }

    public static SimpleCompareWhereClause Create(string column, string op, object? value)
    {
        return new SimpleCompareWhereClause(column, op, value);
    }

    public static SimpleCompareWhereClause Eq(string column, object? value)
    {
        return new SimpleCompareWhereClause(column, "=", value);
    }

    public static SimpleCompareWhereClause Neq(string column, object? value)
    {
        return new SimpleCompareWhereClause(column, "<>", value);
    }

    public static SimpleCompareWhereClause Gt(string column, object? value)
    {
        return new SimpleCompareWhereClause(column, ">", value);
    }

    public static SimpleCompareWhereClause Gte(string column, object? value)
    {
        return new SimpleCompareWhereClause(column, ">=", value);
    }

    public static SimpleCompareWhereClause Lt(string column, object? value)
    {
        return new SimpleCompareWhereClause(column, "<", value);
    }

    public static SimpleCompareWhereClause Lte(string column, object? value)
    {
        return new SimpleCompareWhereClause(column, "<=", value);
    }

    public (string sql, DynamicParameters parameters) GenerateSql(string? dbProviderId = null)
    {
        var parameters = new DynamicParameters();
        var parameterName = parameters.AddRandomNameParameter(Value);
        return ($"{Column} {Operator} @{parameterName}", parameters);
    }
}

public class WhereClause : AndWhereClause
{
    public WhereClause()
    {
    }

    public void Add(IWhereClause subclause)
    {
        Subclauses.Add(subclause);
    }

    public void Eq(string column, object? value)
    {
        Subclauses.Add(SimpleCompareWhereClause.Eq(column, value));
    }
}
