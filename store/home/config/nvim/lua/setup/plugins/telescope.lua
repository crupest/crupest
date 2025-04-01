local function setup()
    local builtin = require('telescope.builtin')
    vim.keymap.set('n', '<leader>/', builtin.live_grep, {})
    vim.keymap.set('n', '<leader>fg', builtin.live_grep, {})
    vim.keymap.set('n', '<leader>ff', builtin.find_files, {})
    vim.keymap.set('n', '<leader>fb', builtin.buffers, {})
    vim.keymap.set('n', '<leader>fh', builtin.help_tags, {})
    vim.keymap.set('n', '<leader>fr', builtin.registers, {})
    vim.keymap.set('n', '<leader>fq', builtin.quickfixhistory, {})
    vim.keymap.set('n', '<leader>fm', builtin.marks, {})
    vim.keymap.set('n', '<leader>fd', builtin.diagnostics, {})
    vim.keymap.set('n', '<leader>fs', builtin.lsp_workspace_symbols, {})

    local function all_files(opts)
        opts = vim.tbl_extend('force', {
            hidden = true,
            no_ignore = true,
            no_ignore_parent = true,
        }, opts or {})
        builtin.find_files(opts)
    end

    vim.keymap.set('n', '<leader>fa', all_files, {})
end

return {
    setup = setup
}
