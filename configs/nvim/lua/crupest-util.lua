local M = {}

M.clean_path = function (path)
    return string.gsub(path, "[/\\]+", "/")
end

M.get_exe = function (path)
    if vim.fn.has("win32") then
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

    if vim.fn.executable(path) then
        return path
    end
    return nil
end

M.walk_up = function (path, func)
    local current_path = vim.fn.fnamemodify(path, ":p")
    while true do
        print(current_path)
        local result = func(current_path)
        if result then
            return result
        end
        local new_path = vim.fn.fnamemodify(current_path, ":p:h")
        print(new_path)
        if new_path == current_path then
            break
        end
    end
    return nil
end

M.find_node_modules = function (path)
    return M.walk_up(path, function (current_path)
        local node_modules_path = current_path.."/node_modules"
        if vim.fn.isdirectory(node_modules_path) then
            return node_modules_path
        end
        return nil
    end)
end

M.find_npm_exe = function (path, exe)
    local node_modules_path = M.find_node_modules(path)
    if not node_modules_path then return nil end
    local exe_path = M.get_exe(node_modules_path.."/.bin/"..exe)
    if exe_path then return M.clean_path(exe_path) end
    return nil
end

return M
