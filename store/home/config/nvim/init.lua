if vim.g.neovide then
    -- spellchecker: disable-next-line
    vim.opt.guifont = "FiraCode Nerd Font";
    vim.g.neovide_normal_opacity = 0.95;
    vim.g.neovide_input_ime = false;
    vim.g.neovide_cursor_animate_in_insert_mode = false
    vim.g.neovide_input_macos_option_key_is_meta = 'only_left'
end

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
require("lazy").setup("plugins")

vim.cmd("colorscheme catppuccin-macchiato")

require("setup").setup()

