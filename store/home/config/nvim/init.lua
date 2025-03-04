if vim.g.neovide then
    -- spellchecker: disable-next-line
    vim.opt.guifont = "FiraCode Nerd Font";
    vim.g.neovide_normal_opacity = 0.95;
    vim.g.neovide_input_ime = false;
    vim.g.neovide_cursor_animate_in_insert_mode = false
    vim.g.neovide_input_macos_option_key_is_meta = 'only_left'
end

local is_win = vim.fn.has("win32") ~= 0

-- spellchecker: disable
if is_win then
    vim.cmd([[
    let &shell = executable('pwsh') ? 'pwsh' : 'powershell'
    let &shellcmdflag = '-NoLogo -ExecutionPolicy RemoteSigned -Command [Console]::InputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();$PSDefaultParameterValues[''Out-File:Encoding'']=''utf8'';Remove-Alias -Force -ErrorAction SilentlyContinue tee;'
    let &shellredir = '2>&1 | %%{ "$_" } | Out-File %s; exit $LastExitCode'
    let &shellpipe  = '2>&1 | %%{ "$_" } | tee %s; exit $LastExitCode'
    set shellquote= shellxquote=
    ]])
    vim.opt.completeslash = 'slash'
end
-- spellchecker: enable

-- spellchecker: disable
vim.opt.termguicolors = true;
vim.opt.fileformats = "unix,dos";
vim.opt.softtabstop = 4;
vim.opt.shiftwidth = 4;
vim.opt.expandtab = true;
vim.opt.wrap = false;
vim.opt.number = true;
-- spellchecker: enable

vim.g.load_doxygen_syntax = true;
vim.g.doxygen_javadoc_autobrief = false;

-- Init lazy.nvim
local lazy_path = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.uv.fs_stat(lazy_path) then
    vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable", -- latest stable release
        lazy_path,
    })
end
vim.opt.rtp:prepend(lazy_path)

-- Use lazy.nvim
require("lazy").setup("plugins")

vim.cmd("colorscheme catppuccin-macchiato")

require("crupest.nvim.lsp").setup()
require("crupest.nvim.plugins").setup()
require("crupest.nvim.keymap").setup()

vim.cmd("autocmd FileType gitcommit,gitrebase,gitconfig set bufhidden=delete")
