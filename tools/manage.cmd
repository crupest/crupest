@echo off

set PYTHON=py -3
%PYTHON% --version >NUL 2>&1 || (
    echo Error: failed to run Python with py -3 --version.
    exit 1
)

set TOOLS_DIR=%~dp0
set PROJECT_DIR=%TOOLS_DIR%..

cd /d "%PROJECT_DIR%"

set PYTHONPATH=%PROJECT_DIR%\tools\cru-py;%PYTHONPATH%
%PYTHON%  -m cru.service --project-dir "%PROJECT_DIR%" %*
