local function setup()
    local installed = require("nvim-treesitter").get_installed()
    if #installed ~= 0 then
        vim.api.nvim_create_autocmd('FileType', {
            pattern = installed,
            callback = function()
                vim.treesitter.start()
                vim.bo.indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
                vim.wo[0][0].foldexpr = 'v:lua.vim.treesitter.foldexpr()'
                vim.wo[0][0].foldmethod = 'expr'
                vim.cmd("normal! zR")
            end,
        })
    end
end

return {
    setup = setup
}
