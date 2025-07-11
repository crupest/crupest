vim.crupest = {}

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
require("lazy").setup {
    spec = { { import = "plugins" } }
}

vim.cmd([[
    if has('nvim') && executable('nvr')
        let $GIT_EDITOR = 'nvr -cc split --remote-wait'
    endif
]])

if vim.g.neovide or vim.env.ALACRITTY_WINDOW_ID then
    vim.opt.guifont = "Maple Mono";
    vim.g.neovide_normal_opacity = 0.95;
    vim.g.neovide_input_ime = false;
    vim.g.neovide_cursor_animate_in_insert_mode = false
    vim.g.neovide_scroll_animation_far_lines = 0
    vim.g.neovide_input_macos_option_key_is_meta = 'only_left'
    vim.cmd("colorscheme catppuccin-macchiato")
end

require("setup").setup()
