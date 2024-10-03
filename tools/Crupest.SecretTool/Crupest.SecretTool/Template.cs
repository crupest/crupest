using System.Diagnostics.CodeAnalysis;
using System.Text;

namespace Crupest.SecretTool;

public class Template
{
    private enum ParseState
    {
        Text,
        Dollar,
        LeftBracket,
        VariableName,
        VariableNameFinish,
    }

    private interface ITemplateNode
    {
        string Render(Dictionary<string, string> values);
    }

    private class TextNode(string text) : ITemplateNode
    {

        public string Text { get; } = text;

        public string Render(Dictionary<string, string> values)
        {
            return Text;
        }
    }

    private class VariableNode(string variableName) : ITemplateNode
    {
        public string VariableName { get; } = variableName;

        public string Render(Dictionary<string, string> values)
        {
            return values.GetValueOrDefault(VariableName) ?? "";
        }
    }

    public Template(string templateString)
    {
        TemplateString = templateString;
        Nodes = Parse(templateString);
        VariableNames = Nodes.OfType<VariableNode>().Select(node => node.VariableName).ToList();
    }

    private static List<ITemplateNode> Parse(string templateString)
    {
        int lineNumber = 1;
        int columnNumber = 0;
        List<ITemplateNode> nodes = [];
        ParseState state = ParseState.Text;
        StringBuilder stringBuilder = new();

        string GetPosition() => $"line {lineNumber} column{columnNumber}";

        [DoesNotReturn]
        void ReportInvalidState(string message)
        {
            throw new Exception($"Invalid state at {GetPosition()}: {message}");
        }

        [DoesNotReturn]
        void ReportInvalidCharacter(char c)
        {
            throw new FormatException($"Unexpected '{c}' at {GetPosition()}.");
        }

        void FinishText()
        {
            if (state != ParseState.Text)
            {
                ReportInvalidState($"Can't call FinishText here.");
            }

            if (stringBuilder.Length > 0)
            {
                nodes.Add(new TextNode(stringBuilder.ToString()));
                stringBuilder.Clear();
            }
        }

        foreach (var c in templateString)
        {
            if (c == '\n')
            {
                lineNumber++;
                columnNumber = 0;
            }

            columnNumber++;

            switch (c)
            {
                case '$':
                    if (state == ParseState.Text)
                    {
                        FinishText();
                        state = ParseState.Dollar;
                    }
                    else if (state == ParseState.Dollar)
                    {
                        if (stringBuilder.Length > 0)
                        {
                            throw new Exception($"Invalid state at {GetPosition()}: when we meet the second '$', text builder should be empty.");
                        }
                        stringBuilder.Append(c);
                        state = ParseState.Text;
                    }
                    else
                    {
                        throw new FormatException($"Unexpected '$' at {GetPosition()}.");
                    }
                    break;
                case '{':
                    if (state == ParseState.Text)
                    {
                        stringBuilder.Append(c);
                    }
                    else if (state == ParseState.Dollar)
                    {
                        state = ParseState.LeftBracket;
                    }
                    else
                    {
                        throw new Exception($"Unexpected '{{' at {GetPosition()}.");
                    }
                    break;
                case '}':
                    if (state == ParseState.Text)
                    {
                        stringBuilder.Append(c);
                        state = ParseState.Text;
                    }
                    else if (state == ParseState.VariableName || state == ParseState.VariableNameFinish)
                    {
                        nodes.Add(new VariableNode(stringBuilder.ToString()));
                        stringBuilder.Clear();
                        state = ParseState.Text;
                    }
                    else
                    {
                        ReportInvalidCharacter(c);
                    }
                    break;
                default:
                    if (state == ParseState.Dollar)
                    {
                        ReportInvalidCharacter(c);
                    }

                    if (char.IsWhiteSpace(c))
                    {
                        if (state == ParseState.LeftBracket || state == ParseState.VariableNameFinish)
                        {
                            continue;
                        }
                        else if (state == ParseState.Text)
                        {
                            stringBuilder.Append(c);
                        }
                        else if (state == ParseState.VariableName)
                        {
                            state = ParseState.VariableNameFinish;
                        }
                        else
                        {
                            ReportInvalidCharacter(c);
                        }
                    }
                    else
                    {
                        if (state == ParseState.Text)
                        {
                            stringBuilder.Append(c);
                        }
                        else if (state == ParseState.LeftBracket || state == ParseState.VariableName)
                        {
                            stringBuilder.Append(c);
                            state = ParseState.VariableName;
                        }
                        else
                        {
                            ReportInvalidCharacter(c);
                        }
                    }
                    break;
            }
        }

        if (state == ParseState.Text)
        {
            FinishText();
        }
        else
        {
            throw new FormatException("Unexpected end of template string.");
        }

        return nodes;
    }

    public string TemplateString { get; }
    private List<ITemplateNode> Nodes { get; set; }
    public List<string> VariableNames { get; }

    public string Generate(Dictionary<string, string> values, bool allowMissingVariable = false)
    {
        StringBuilder stringBuilder = new();
        foreach (var node in Nodes)
        {
            if (node is TextNode textNode)
            {
                stringBuilder.Append(textNode.Text);
            }
            else if (node is VariableNode variableNode)
            {
                var hasValue = values.TryGetValue(variableNode.VariableName, out var value);
                if (!hasValue && !allowMissingVariable)
                {
                    throw new Exception($"Variable '{variableNode.VariableName}' is not set.");
                }
                stringBuilder.Append(hasValue ? value : string.Empty);
            }
        }
        return stringBuilder.ToString();
    }
}
