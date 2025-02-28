if ($args.Count -ne 1 || $args[0] -notmatch "^win-x64|linux-x64|osx-x64$")
{
    Write-Error "You must specify exactly one argument, the build target (win-x64 | linux-x64 | osx-x64)."
    exit 1
}

Write-Output "Secret dir: $PSScriptRoot"

Write-Output "Check dotnet..."
dotnet --version
if ($LASTEXITCODE -ne 0)
{
    Write-Error "dotnet not found."
    exit 2
}

Write-Output "Enter `"secret`" dir..."
Push-Location $PSScriptRoot

Write-Output "Begin to build..."
dotnet publish Crupest.SecretTool -c Release -o "$secret_dir/publish" --sc -r $args[0]

Pop-Location

Write-Host "Finish!" -ForegroundColor Green
