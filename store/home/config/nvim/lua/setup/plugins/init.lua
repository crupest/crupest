local function setup()
    require("setup.plugins.lint").setup()
    require("setup.plugins.cmp").setup()
    require("setup.plugins.telescope").setup()
    require("setup.plugins.gitsigns").setup()

    require('lualine').setup {}
    require("nvim-tree").setup {}
    require("nvim-autopairs").setup {}
end

return {
    setup = setup
}
