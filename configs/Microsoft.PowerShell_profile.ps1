Import-Module posh-git
Import-Module "$env:VCPKG_INSTALLATION_ROOT\scripts\posh-vcpkg"

function Use-VC {
    param(
        [Parameter()]
        [ValidateSet('x64', 'x86')]
        $Arch = 'x64'
    )

    if ($Arch -eq 'x86') {
        $p = 'x86';
    }
    else {
        $p = 'amd64'
    }

    cmd /c "`"$(vswhere.exe -format value -property installationPath)\VC\Auxiliary\Build\vcvars64.bat`" $p & set" |
    ForEach-Object {
        if ($_ -match '=') {
            $v = $_ -split '='
            Set-Item -Force -Path "ENV:\$($v[0])" -Value "$($v[1])"
        }
    }
    Pop-Location
    Write-Host "Visual Studio Command Prompt variables set." -ForegroundColor Yellow
}


function Set-Proxy {
    $env:http_proxy = "http://localhost:2080"
    $env:https_proxy = "http://localhost:2080"
}

function Reset-Proxy {
    Remove-Item env:http_proxy
    Remove-Item env:https_proxy
}
