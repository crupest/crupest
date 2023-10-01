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

local function get_previous_buffer(buf)
    local bufs = list_listed_bufs()

    -- no buffers at all
    if #bufs == 0 then return nil end

    -- find the buf in bufs
    local index = 0
    for i, v in ipairs(bufs) do
        if buf == v then
            index = i
            break
        end
    end

    -- it's the only one
    if #bufs == 1 and index == 1 then
        return nil
    end

    -- it's the first one
    if index == 1 then
        return bufs[2]
    end

    return bufs[index - 1]
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

-- Delete current buffer and jump back.
-- If no previous jump, switch to previous buffer.
-- If no previous buffer (no other buffers), create a unnamed one. (So the window does not quit.)
local function win_close_buf()
    local buf = vim.api.nvim_get_current_buf()

    if  not buf_is_normal(buf) then
        return
    end

    local jumps_info = vim.fn.getjumplist()

    local old_jumps = { unpack(jumps_info[1], 1, jumps_info[2]) }
    while #old_jumps ~= 0 do
        local last_jump = old_jumps[#old_jumps]
        if last_jump.bufnr ~= buf and vim.fn.bufexists(last_jump.bufnr) ~= 0 and vim.fn.buflisted(last_jump.bufnr) ~= 0 then
            break
        end
        table.remove(old_jumps, #old_jumps)
    end

    if #old_jumps ~= 0 then
        local last_jump = old_jumps[#old_jumps]
        vim.api.nvim_win_set_buf(0, last_jump.bufnr)
        vim.api.nvim_win_set_cursor(0, {last_jump.lnum, last_jump.col})
    else
        local previous_buf = get_previous_buffer(buf)
        if previous_buf then
            vim.api.nvim_win_set_buf(0, previous_buf)
        else
            local new_buf = vim.api.nvim_create_buf(true, false)
            vim.api.nvim_win_set_buf(0, new_buf)
        end
    end

    local wins = list_wins_editing_buf(buf)
    if #wins == 0 then
        vim.api.nvim_buf_delete(buf, {})
    end
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
    get_previous_buffer = get_previous_buffer,
    list_wins_editing_buf = list_wins_editing_buf,
    win_close_buf = win_close_buf,
    close_float = close_float,
}

