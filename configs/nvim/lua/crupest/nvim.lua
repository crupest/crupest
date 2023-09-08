local fs = require("crupest.system.fs")

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

local function full_path(name)
    return vim.fn.fnamemodify(name, ":p:gs?\\?/?")
end

local function coerce_path_for_dir(old, new)
    if fs.isdir(new) then
        return new .. "/" .. vim.fn.fnamemodify(old, ":t")
    end
    return new
end

local function do_mv_file(old, new, overwrite)
    new = coerce_path_for_dir(old, new)

    if full_path(old) == full_path(new) then
        vim.notify("Paths are identical. Do nothing.", vim.log.levels.WARN)
        return false
    end

    if not fs.isfile(old) then
        vim.notify("Not exists or not a file. Can't move.", vim.log.levels.ERROR)
        return false
    end

    if not overwrite and fs.exist(new) then
        vim.notify("Target path exists.", vim.log.levels.ERROR)
        return false
    end

    fs.move(old, new)
    vim.notify("File moved.")

    return new
end

local function mv_file(old, new, overwrite)
    new = do_mv_file(old, new, overwrite)
    if not new then return end

    local bufs = list_listed_bufs()
    for _, b in ipairs(bufs) do
        if full_path(vim.api.nvim_buf_get_name(b)) == full_path(old) then
            vim.api.nvim_buf_set_name(b, new)
        end
    end
end

local function mv_buf_file(buf, new, overwrite)
    if not buf_is_normal(buf) then
        vim.notify("Buf is not a normal buffer, can't move it.", vim.log.levels.ERROR)
        return
    end

    local name = vim.api.nvim_buf_get_name(buf)

    new = do_mv_file(name, new, overwrite)
    if not new then return end

    vim.api.nvim_buf_set_name(buf, new)
end

local function mv_dir(old_dir, new_dir, overwrite)
    new_dir = coerce_path_for_dir(old_dir, new_dir)

    if full_path(old_dir) == full_path(new_dir) then
        vim.notify("Paths are identical. Do nothing.", vim.log.levels.WARN)
        return
    end

    if not fs.isdir(old_dir) then
        vim.notify("Not exist or not a dir. Can't move.", vim.log.levels.ERROR)
    end

    if not overwrite and fs.exist(new_dir) then
        vim.notify("Target path exists.", vim.log.levels.ERROR)
        return
    end

    if fs.isdir(old_dir) then
        fs.move(old_dir, new_dir)
        vim.notify("Dir moved.")
    end

    local bufs = list_listed_bufs()

    for _, buf in ipairs(bufs) do
        local name = vim.api.nvim_buf_get_name(buf)
        local full_name = full_path(name)
        local old_dir_full = full_path(old_dir)
        if string.find(full_name, old_dir_full, 1, true) == 1 then
            local new_name = new_dir .. string.sub(full_name, #old_dir_full + 1)
            vim.api.nvim_buf_set_name(buf, new_name)
        end
    end
end

local function rename_file(old, new, overwrite)
    local dir = vim.fn.fnamemodify(old, ":h")
    mv_file(old, dir .. "/" .. new, overwrite)
end

local function rename_buf_file(buf, new_name, overwrite)
    local old_path = vim.api.nvim_buf_get_name(buf)
    local dir = vim.fn.fnamemodify(old_path, ":h")
    mv_buf_file(buf, dir .. "/" .. new_name, overwrite)
end

return {
    list_listed_bufs = list_listed_bufs,
    get_previous_buffer = get_previous_buffer,
    list_wins_editing_buf = list_wins_editing_buf,
    win_close_buf = win_close_buf,
    close_float = close_float,
    mv_file = mv_file,
    mv_buf_file = mv_buf_file,
    mv_dir = mv_dir,
    rename_file = rename_file,
    rename_buf_file = rename_buf_file
}

