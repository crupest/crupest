local function setup()
    local gitsigns = require('gitsigns')

    gitsigns.setup {
        on_attach = function(bufnr)
            local function map(mode, l, r, opts)
                opts = opts or {}
                opts.buffer = bufnr
                vim.keymap.set(mode, l, r, opts)
            end

            -- Navigation
            map('n', ']c', function()
                if vim.wo.diff then
                    vim.cmd.normal({ ']c', bang = true })
                else
                    gitsigns.nav_hunk('next')
                end
            end)

            map('n', '[c', function()
                if vim.wo.diff then
                    vim.cmd.normal({ '[c', bang = true })
                else
                    gitsigns.nav_hunk('prev')
                end
            end)

            -- Actions
            map('n', '<leader>gc', gitsigns.preview_hunk)
            map('n', '<leader>gt', gitsigns.toggle_deleted)
            map('n', '<leader>gd', gitsigns.diffthis)
            map('n', '<leader>gb', function() gitsigns.blame_line { full = true } end)
        end
    }
end

return {
    setup = setup
}
