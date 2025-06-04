local function setup()
    require("neo-tree").setup {}
    require('lualine').setup {}

    require("setup.plugins.telescope").setup()
    require("setup.plugins.gitsigns").setup()

    require("setup.plugins.tree-sitter").setup()
    require("setup.plugins.lint").setup()
    require("setup.plugins.cmp").setup()
    require("nvim-autopairs").setup {}
end

return {
    setup = setup
}
