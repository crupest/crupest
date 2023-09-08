local function clean_path(path)
    return path and (string.gsub(path, "[/\\]+", "/"))
end

local function get_exe(path)
    if vim.fn.has("win32") ~= 0 then
        local suffixes = { ".exe", ".CMD", ".cmd", ".ps1" }
        for _, v in ipairs(suffixes) do
            if string.find(path, v.."$") and vim.uv.fs_stat(path) then
                return path
            end
        end
        for _, v in ipairs(suffixes) do
            local p = path..v
            if vim.uv.fs_stat(p) then return p end
        end
        return nil
    end

    if vim.fn.executable(path) ~= 0 then
        return path
    end

    return nil
end

local function walk_up(path, func)
    local current_path = vim.fn.fnamemodify(path, ":p")
    while true do
        local result = func(current_path)
        if result then
            return result
        end
        local new_path = vim.fn.fnamemodify(current_path, ":h")
        if new_path == current_path then
            break
        end
        current_path = new_path
    end
    return nil
end

local function find_node_modules(path)
    return walk_up(path, function (current_path)
        local node_modules_path = current_path.."/node_modules"
        if vim.fn.isdirectory(node_modules_path) ~= 0 then
            return node_modules_path
        end
        return nil
    end)
end

local function find_npm_exe(path, exe)
    local node_modules_path = find_node_modules(path)
    if not node_modules_path then return nil end
    local try_exe_path = node_modules_path.."/.bin/"..exe
    local exe_path = get_exe(try_exe_path)
    if exe_path then return clean_path(exe_path) end
    return nil
end

return {
    clean_path = clean_path,
    get_exe = get_exe,
    walk_up = walk_up,
    find_node_modules = find_node_modules,
    find_npm_exe = find_npm_exe
}

