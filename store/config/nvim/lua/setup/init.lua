local function setup()
    if vim.fn.has("win32") ~= 0 then
        require("setup.win").setup()
    end

    vim.opt.termguicolors = true;
    vim.opt.fileformats = "unix,dos";
    vim.opt.number = true;

    vim.g.load_doxygen_syntax = true;
    vim.g.doxygen_javadoc_autobrief = false;

    vim.keymap.set("n", "<c-tab>", "<cmd>bnext<cr>")
    vim.keymap.set("n", "<c-s-tab>", "<cmd>bNext<cr>")
    vim.keymap.set("n", "<esc>", function()
        local float_closed = false
        local wins = vim.api.nvim_list_wins()
        for _, v in ipairs(wins) do
            if vim.api.nvim_win_get_config(v).relative ~= '' then
                vim.api.nvim_win_close(v, false)
                float_closed = true
            end
        end
        if not float_closed then
            vim.cmd("nohlsearch")
        end
    end)
    vim.keymap.set("n", "<C-q>", function()
        require("mini.bufremove").delete()
    end)
    vim.keymap.set('t', '<A-n>', '<C-\\><C-n>')
    vim.keymap.set('t', '<A-p>', function()
        local register = vim.fn.input("Enter register: ")
        if register == "" then
            register = '"'
        end
        return '<C-\\><C-N>"' .. register .. 'pi'
    end, { expr = true })

    vim.cmd("autocmd FileType gitcommit,gitrebase,gitconfig set bufhidden=delete")

    vim.diagnostic.config({ virtual_text = true })
    vim.keymap.set("n", "grl", vim.diagnostic.open_float)

    require("setup.lsp").setup()
    require("setup.plugins").setup()

    vim.keymap.set("n", "<leader>sf", "<cmd>Neotree<cr>")
    vim.keymap.set("n", "<leader>st", "<cmd>ToggleTerm<cr>")
end

return {
    setup = setup
}
