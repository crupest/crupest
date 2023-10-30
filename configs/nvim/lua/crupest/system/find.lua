local system = require("crupest.system")
local fs = require("crupest.system.fs");

local function get_exe(path)
    if system.is_win then
        local exts = { "exe", "CMD", "cmd", "ps1" }
        for _, ext in ipairs(exts) do
            if string.find(path, "%." .. ext .. "$") and fs.isfile(path) then
                return path
            end
        end
        for _, ext in ipairs(exts) do
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

local function first_exe(paths)
    for _, v in ipairs(paths) do
        local exe = get_exe(v)
        if exe then return exe end
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

return {
    get_exe = get_exe,
    first_exe = first_exe,
    find_node_modules = find_node_modules,
    find_npm_exe = find_npm_exe,
}
