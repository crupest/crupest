local function list_listed_bufs()
    local bufs = vim.api.nvim_list_bufs()
    local result = {}
    for _, v in ipairs(bufs) do
        if vim.fn.buflisted(v) ~= 0 then
            table.insert(result, v)
        end
    end
    return result
end

-- list the windows that are currently editing the given buffer
local function list_wins_editing_buf(buf)
    local wins = vim.api.nvim_list_wins()
    local result = {}
    for _, win in ipairs(wins) do
        if vim.api.nvim_win_get_buf(win) == buf then
            table.insert(result, win)
        end
    end
    return result
end

local function buf_is_normal(buf)
    return vim.fn.bufexists(buf) ~= 0 and vim.fn.buflisted(buf) ~= 0
end


local function close_float()
    local wins = vim.api.nvim_list_wins()
    for _, v in ipairs(wins) do
        if vim.api.nvim_win_get_config(v).relative ~= '' then
            vim.api.nvim_win_close(v, false)
        end
    end
end

return {
    list_listed_bufs = list_listed_bufs,
    buf_is_normal = buf_is_normal,
    list_wins_editing_buf = list_wins_editing_buf,
    close_float = close_float,
}

