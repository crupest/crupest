namespace CrupestApi.Commons.Crud;

[System.Serializable]
public class DatabaseInternalException : System.Exception
{
    public DatabaseInternalException() { }
    public DatabaseInternalException(string message) : base(message) { }
    public DatabaseInternalException(string message, System.Exception inner) : base(message, inner) { }
    protected DatabaseInternalException(
        System.Runtime.Serialization.SerializationInfo info,
        System.Runtime.Serialization.StreamingContext context) : base(info, context) { }
}