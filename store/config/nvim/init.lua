vim.crupest = {}

local gh = function(x) return 'https://github.com/' .. x end

--- spellchecker: disable
vim.pack.add({
    {
        name = "catppuccin",
        src = gh("catppuccin/nvim"),
    },
    gh("neovim/nvim-lspconfig"),
    {
        src = gh("nvim-treesitter/nvim-treesitter"),
        version = "master",
    },
    gh("nvim-tree/nvim-web-devicons"),
    gh("nvim-lua/plenary.nvim"),
    gh("MunifTanjim/nui.nvim"),
    {
        src = gh("nvim-neo-tree/neo-tree.nvim"),
        version = "v3.x",
    },
    gh("nvim-lualine/lualine.nvim"),
    gh("nvim-telescope/telescope.nvim"),
    gh("lewis6991/gitsigns.nvim"),
    gh("sindrets/diffview.nvim"),
    gh("hrsh7th/nvim-cmp"),
    gh("hrsh7th/cmp-nvim-lsp"),
    gh("hrsh7th/cmp-buffer"),
    gh("hrsh7th/cmp-path"),
    gh("echasnovski/mini.bufremove"),
    gh("windwp/nvim-autopairs"),
    gh("mfussenegger/nvim-lint"),
    gh("akinsho/toggleterm.nvim"),
})
--- spellchecker: enable

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
