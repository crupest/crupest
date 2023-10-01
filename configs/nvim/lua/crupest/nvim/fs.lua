local list_listed_bufs = require("crupest.nvim").list_listed_bufs;
local fs = require("crupest.system.fs");

local function full_path(name)
    return vim.fn.fnamemodify(name, ":p:gs?\\?/?")
end

-- There are two situations.
-- 1. the new path is not a dir, then it is used
-- 2. the new path is a dir, then it is appended with the last name of old path, to create a new valid file path
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

local function setup_filesystem_user_commands()
    vim.api.nvim_create_user_command("Mv", function(opts)
        mv_buf_file(vim.api.nvim_get_current_buf(), opts.fargs[1])
    end, {
        nargs = 1,
        complete = "file"
    })

    vim.api.nvim_create_user_command("MvFile", function(opts)
        if (#opts.fargs ~= 2) then
            vim.notify("MvFile accepts exactly two arguments, old file and new file.")
        end
        mv_file(opts.fargs[1], opts.fargs[2])
    end, {
        nargs = "+",
        complete = "file"
    })

    vim.api.nvim_create_user_command("MvDir", function(opts)
        if (#opts.fargs ~= 2) then
            vim.notify("MvDir accepts exactly two arguments, old dir and new dir.")
        end
        mv_dir(opts.fargs[1], opts.fargs[2])
    end, {
        nargs = "+",
        complete = "file"
    })

    vim.api.nvim_create_user_command("Rename", function(opts)
        rename_buf_file(vim.api.nvim_get_current_buf(), opts.fargs[1])
    end, {
        nargs = 1,
        complete = "file"
    })

    vim.api.nvim_create_user_command("RenameFile", function(opts)
        if (#opts.fargs ~= 2) then
            vim.notify("RenameFile accepts exactly two arguments, old file and new file.")
        end
        rename_file(opts.fargs[1], opts.fargs[2])
    end, {
        nargs = "+",
        complete = "file"
    })
end

return {
    mv_file = mv_file,
    mv_buf_file = mv_buf_file,
    mv_dir = mv_dir,
    rename_file = rename_file,
    rename_buf_file = rename_buf_file,
    setup_filesystem_user_commands = setup_filesystem_user_commands
}

