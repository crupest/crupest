local function setup()
    vim.keymap.set("n", "<c-tab>", "<cmd>bnext<cr>")
    vim.keymap.set("n", "<c-s-tab>", "<cmd>bNext<cr>")
    vim.keymap.set("n", "<esc>", require("crupest.utils.nvim").close_float)
end

return {
    setup = setup
}
