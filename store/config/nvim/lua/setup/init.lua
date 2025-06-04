-- spellchecker: words termguicolors

local function close_float()
    local wins = vim.api.nvim_list_wins()
    for _, v in ipairs(wins) do
        if vim.api.nvim_win_get_config(v).relative ~= '' then
            vim.api.nvim_win_close(v, false)
        end
    end
end

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
    vim.keymap.set("n", "<esc>", close_float)
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
end

return {
    setup = setup
}
