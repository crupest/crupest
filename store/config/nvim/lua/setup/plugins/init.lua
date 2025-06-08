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

    require("setup.plugins.tree-sitter").setup()
    require("setup.plugins.lint").setup()
    require("setup.plugins.conform").setup()
    require("setup.plugins.cmp").setup()
    require("nvim-autopairs").setup {}
end

return {
    setup = setup
}
