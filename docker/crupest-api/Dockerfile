FROM mcr.microsoft.com/dotnet/sdk:7.0-alpine AS build
COPY CrupestApi /CrupestApi
WORKDIR /CrupestApi
RUN dotnet publish CrupestApi/CrupestApi.csproj --configuration Release --output ./publish -r linux-x64

FROM mcr.microsoft.com/dotnet/aspnet:7.0-alpine
ENV ASPNETCORE_URLS=http://0.0.0.0:5000
ENV ASPNETCORE_FORWARDEDHEADERS_ENABLED=true
COPY --from=build /CrupestApi/publish /CrupestApi
WORKDIR /CrupestApi
VOLUME [ "/crupest-api-config.json" ]
EXPOSE 5000
ENTRYPOINT ["dotnet", "CrupestApi.dll"]
