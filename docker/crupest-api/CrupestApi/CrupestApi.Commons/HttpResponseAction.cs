namespace CrupestApi.Commons;

public delegate void HttpResponseAction(HttpResponse response);
public delegate Task AsyncHttpResponseAction(HttpResponse response);
