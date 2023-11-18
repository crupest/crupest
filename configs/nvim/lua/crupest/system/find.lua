local system = require("crupest.system")
local fs = require("crupest.system.fs");

local win_exe_exts = { "exe", "CMD", "cmd", "ps1" }


local function get_exe(path)
    if system.is_win then
        for _, ext in ipairs(win_exe_exts) do
            if string.find(path, "%." .. ext .. "$") and fs.isfile(path) then
                return path
            end
        end
        for _, ext in ipairs(win_exe_exts) do
            local p = path .. "." .. ext
            if fs.isfile(p) then return p end
        end
        return nil
    end

    if vim.fn.executable(path) ~= 0 then
        return path
    end

    return nil
end

local function find_global_exe(name)
    if vim.fn.executable(name) ~= 0 then
        return name
    end

    return nil
end

local function first_exe(paths)
    for _, v in ipairs(paths) do
        local exe = get_exe(v)
        if exe then return exe end
    end

    return nil
end

local function find_file_or_directory(path, name)
    return fs.walk_up(path, function(current_path)
        local p = current_path .. "/" .. name
        if fs.isdir(p) then
            return p, "directory"
        elseif fs.isfile(p) then
            return p, "file"
        end
        return nil
    end)
end

local function find_file(path, name)
    return fs.walk_up(path, function(current_path)
        local p = current_path .. "/" .. name
        if fs.isfile(p) then
            return p
        end
        return nil
    end)
end

local function find_files_or_directories(path, names)
    for _, name in ipairs(names) do
        local p, type = find_file_or_directory(path, name)
        if p then return p, type end
    end
    return nil
end

local function find_files(path, names)
    for _, name in ipairs(names) do
        local p = find_file(path, name)
        if p then return p end
    end
    return nil
end

local function find_node_modules(path)
    return fs.walk_up(path, function(current_path)
        local node_modules_path = current_path .. "/node_modules"
        if fs.isdir(node_modules_path) then
            return node_modules_path
        end
        return nil
    end)
end

local function find_npm_exe(path, exe)
    local node_modules_path = find_node_modules(path)
    if not node_modules_path then return nil end
    local try_exe_path = node_modules_path .. "/.bin/" .. exe
    local exe_path = get_exe(try_exe_path)
    if exe_path then return exe_path end
    return nil
end

local function find_exe(path, exe, places)
    for _, place in ipairs(places) do
        if place == "npm" then
            local r = find_npm_exe(path, exe)
            if r then return r end
        end
        if place == "global" then
            local r = find_global_exe(exe)
            if r then return r end
        end
    end
    return nil
end

local function find_exe_for_buf(buf, opts)
    local r = {}
    r.name = opts.name
    r.file = vim.api.nvim_buf_get_name(buf)
    r.filetype = vim.api.nvim_buf_get_option(buf, "filetype")
    r.exe_name = opts.name
    r.exe_places = opts.exe_places or { "global" }

    if opts.config_files then
        r.config_file = find_files(r.file, opts.config_files)
        if r.config_file == nil then return nil end
    end

    if opts.filetypes then
        if not require("crupest.table").includes(opts.filetypes, r.filetype) then
            return nil
        end
    end

    r.exe_path = find_exe(r.file, r.exe_name, r.exe_places)
    if r.exe_path == nil then return nil end

    return r
end

return {
    get_exe = get_exe,
    find_global_exe = find_global_exe,
    first_exe = first_exe,
    find_file_or_directory = find_file_or_directory,
    find_files_or_directories = find_files_or_directories,
    find_file = find_file,
    find_files = find_files,
    find_node_modules = find_node_modules,
    find_npm_exe = find_npm_exe,
    find_exe = find_exe,
    find_exe_for_buf = find_exe_for_buf,
}
