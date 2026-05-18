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

    require("setup.plugins.telescope").setup()
    require("setup.plugins.gitsigns").setup()
    require("diffview").setup {}

    require("setup.plugins.tree-sitter").setup()
    require("setup.plugins.lint").setup()
    require("setup.plugins.cmp").setup()
    require("nvim-autopairs").setup {}
    require('mini.bufremove').setup {}
    require("toggleterm").setup()

    require("setup.plugins.codecompanion").setup()
    require('render-markdown').setup {
        file_types = { "markdown", "codecompanion" }
    }
end

return {
    setup = setup
}
