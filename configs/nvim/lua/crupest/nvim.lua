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

local function win_close_buf()
    local current_buffer = vim.api.nvim_get_current_buf()
    local jumps_info = vim.fn.getjumplist()

    local old_jump_list = { unpack(jumps_info[1], 1, jumps_info[2]) }
    while #old_jump_list ~= 0 do
        local last_jump = old_jump_list[#old_jump_list]
        if last_jump.bufnr ~= current_buffer and vim.fn.bufexists(last_jump.bufnr) ~= 0 and vim.fn.buflisted(last_jump.bufnr) ~= 0 then
            break
        end
        table.remove(old_jump_list, #old_jump_list)
    end

    if #old_jump_list ~= 0 then
        local last_jump = old_jump_list[#old_jump_list]
        vim.api.nvim_win_set_buf(0, last_jump.bufnr)
        vim.api.nvim_win_set_cursor(0, {last_jump.lnum, last_jump.col})
    else
        local previous_buf = get_previous_buffer(current_buffer)
        if previous_buf then
            vim.api.nvim_win_set_buf(0, previous_buf)
        else
            local new_buf = vim.api.nvim_create_buf(true, false)
            vim.api.nvim_win_set_buf(0, new_buf)
        end
    end

    vim.api.nvim_buf_delete(current_buffer, {})
end

return {
    list_listed_bufs = list_listed_bufs,
    get_previous_buffer = get_previous_buffer,
    list_wins_editing_buf = list_wins_editing_buf,
    win_close_buf = win_close_buf
}

