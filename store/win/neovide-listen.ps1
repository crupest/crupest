$env:NVIM_LISTEN_ADDRESS ??= "\\.\pipe\nvimsocket"

$neovide_args = @()

$MY_NEOVIM_PATH="$HOME/codes/neovim/build/bin/nvim.exe"
if (Get-Item $MY_NEOVIM_PATH -ErrorAction Ignore) {
    Write-Output "Found my neovim at $MY_NEOVIM_PATH."
    $env:VIMRUNTIME="$HOME/codes/neovim/runtime"
    $neovide_args += "--neovim-bin", "$MY_NEOVIM_PATH"
}

$listen_added = $false
foreach ($arg in $args) {
    $neovide_args += $arg
    if ( $arg -eq '--') {
        $neovide_args += "--listen", $env:NVIM_LISTEN_ADDRESS
        $listen_added=$true
    }
}

if (-not $listen_added) {
    $neovide_args += "--", "--listen", $env:NVIM_LISTEN_ADDRESS
}

$neovide_bin = "neovide"
$my_neovide_path = "$HOME/codes/neovide/target/release/neovide.exe"
if (Get-Item $my_neovide_path -ErrorAction Ignore) {
    Write-Output "Found my neovide at $my_neovide_path."
    $neovide_bin = "$my_neovide_path"
}

if (Get-Command nvr -ErrorAction Ignore) {
    Write-Output "Detected nvr, set git editor env."
    $env:GIT_EDITOR = "nvr -cc split --remote-wait"
}

Write-Output "Command is $($neovide_args -join ' ')."
Start-Process $neovide_bin -ArgumentList $neovide_args -Wait
