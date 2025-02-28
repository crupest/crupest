local function setup()
    require("crupest.nvim.plugins.lint").setup()
    require("crupest.nvim.plugins.snip").setup()
    require("crupest.nvim.plugins.cmp").setup()
    require("crupest.nvim.plugins.telescope").setup()
    require("crupest.nvim.plugins.gitsigns").setup()
    require("crupest.nvim.plugins.others").setup()
end

return {
    setup = setup
}
