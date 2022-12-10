using System.Text;

namespace CrupestApi.Commons.Crud.Tests;

public class SqlCompareHelper
{
    private static List<char> SymbolTokens = new List<char>() { '(', ')', ';' };

    public static List<string> SqlExtractWords(string? sql, bool toLower = true)
    {
        var result = new List<string>();

        if (string.IsNullOrEmpty(sql))
        {
            return result;
        }

        var current = 0;

        StringBuilder? wordBuilder = null;

        while (current < sql.Length)
        {
            if (char.IsWhiteSpace(sql[current]))
            {
                if (wordBuilder is not null)
                {
                    result.Add(wordBuilder.ToString());
                    wordBuilder = null;
                }
            }
            else if (SymbolTokens.Contains(sql[current]))
            {
                if (wordBuilder is not null)
                {
                    result.Add(wordBuilder.ToString());
                    wordBuilder = null;
                }
                result.Add(sql[current].ToString());
            }
            else
            {
                if (wordBuilder is not null)
                {
                    wordBuilder.Append(sql[current]);
                }
                else
                {
                    wordBuilder = new StringBuilder();
                    wordBuilder.Append(sql[current]);
                }
            }
            current++;
        }

        if (wordBuilder is not null)
        {
            result.Add(wordBuilder.ToString());
        }

        if (toLower)
        {
            for (int i = 0; i < result.Count; i++)
            {
                result[i] = result[i].ToLower();
            }
        }

        return result;
    }

    public static bool SqlEqual(string left, string right)
    {
        return SqlExtractWords(left) == SqlExtractWords(right);
    }

    [Fact]
    public void TestSqlExtractWords()
    {
        var sql = "SELECT * FROM TableName WHERE (id = @abcd);";
        var words = SqlExtractWords(sql);

        Assert.Equal(new List<string> { "select", "*", "from", "tablename", "where", "(", "id", "=", "@abcd", ")", ";" }, words);
    }
}
