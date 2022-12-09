using System.Text;

namespace CrupestApi.Commons.Crud.Tests;

public class SqlCompareHelper
{
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
            else if (sql[current] == ';')
            {
                if (wordBuilder is not null)
                {
                    result.Add(wordBuilder.ToString());
                    wordBuilder = null;
                }
                result.Add(";");
            }
            else
            {
                if (wordBuilder is not null)
                {
                    wordBuilder.Append(sql[current]);
                }
                else
                {
                    wordBuilder = new StringBuilder(sql[current]);
                }
            }
        }

        if (wordBuilder is not null)
        {
            result.Add(wordBuilder.ToString());
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
        var sql = "SELECT * FROM TableName WHERE id = @abcd;";
        var words = SqlExtractWords(sql);

        Assert.Equal(words, new List<string> { "select", "*", "from", "tablename", "where", "id", "=", "@abcd", ";" });
    }
}
