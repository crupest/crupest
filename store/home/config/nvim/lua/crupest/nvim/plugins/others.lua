local function setup()
    require('lualine').setup {}
    require("nvim-tree").setup {}
    require("nvim-autopairs").setup {}
end

return {
    setup = setup
}
