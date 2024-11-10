namespace CrupestApi.Commons.Crud;

/// <summary>
/// This exception means the exception is caused by user and can be safely shown to user.
/// </summary>
[System.Serializable]
public class UserException : Exception
{
    public UserException() { }
    public UserException(string message) : base(message) { }
    public UserException(string message, System.Exception inner) : base(message, inner) { }
    protected UserException(
        System.Runtime.Serialization.SerializationInfo info,
        System.Runtime.Serialization.StreamingContext context) : base(info, context) { }
}