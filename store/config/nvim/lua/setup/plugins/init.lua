local function setup()
    require('lualine').setup {}
    require("neo-tree").setup {
        filesystem = {
            filtered_items = {
                hide_dotfiles = false,
                hide_gitignored = false,
                hide_hidden = false,
            }
        }
    }

    require("setup.plugins.tree-sitter").setup()
    require("setup.plugins.cmp").setup()
    require("setup.plugins.telescope").setup()
    require("setup.plugins.gitsigns").setup()
    require("setup.plugins.lint").setup()

    require("diffview").setup {}
    require("nvim-autopairs").setup {}
    require('mini.bufremove').setup {}
    require("toggleterm").setup()
    require("sidekick").setup {}
    require('render-markdown').setup {}
end

return {
    setup = setup
}
