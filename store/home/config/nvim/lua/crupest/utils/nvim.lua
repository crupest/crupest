local M = {}

function M.close_float()
    local wins = vim.api.nvim_list_wins()
    for _, v in ipairs(wins) do
        if vim.api.nvim_win_get_config(v).relative ~= '' then
            vim.api.nvim_win_close(v, false)
        end
    end
end

return M
