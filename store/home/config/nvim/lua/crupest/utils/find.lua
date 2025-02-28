local is_win = vim.fn.has("win32") ~= 0

local M = {}

local windows_exe_ext = { "exe", "bat", "cmd", "ps1" }

--- Find real path (with ext) for an executable.
--- @param dir string
--- @param name string | string[]
--- @return string | nil
function M.find_exe_file(dir, name)
    if type(name) == "string" then
        name = { name }
    end
    for _, n in ipairs(name) do
        if vim.uv.fs_stat(vim.fs.joinpath(dir, n)) ~= nil then
            return n
        end
        if is_win then
            for _, ext in ipairs(windows_exe_ext) do
                if vim.uv.fs_stat(vim.fs.joinpath(dir, n .. "." .. ext)) ~= nil then
                    return n .. "." .. ext
                end
            end
        end
    end
    return nil
end

--- Walk up until found an executable in node_modules.
--- @param path string
--- @param name string
--- @return string | nil exe_path Path to the executable.
function M.find_node_modules_exe(path, name)
    local bin_dirs = vim.fs.find("node_modules/.bin", { path = path, upward = true, type = "directory" })
    if #bin_dirs == 0 then return nil end
    local exe = M.find_exe_file(bin_dirs[1], name)
    return exe and vim.fs.joinpath(bin_dirs[1], exe)
end

--- Find executable in PATH.
--- @param name string
--- @return string | nil
function M.find_global_exe(name)
    local exe = vim.fn.exepath(name)
    if exe == "" then return nil end
    return exe
end

--- @alias ExePlace "node_modules" | "global"
--- @param path string
--- @param name string
--- @param places ExePlace[]
--- @return string | nil, ExePlace?
function M.find_exe(path, name, places)
    for _, place in ipairs(places) do
        if place == "node_modules" then
            local r = M.find_node_modules_exe(path, name)
            if r then return r, "node_modules" end
        end
        if place == "global" then
            local r = M.find_global_exe(name)
            if r then return r, "global" end
        end
    end
    return nil, nil
end

--- @alias FindExeForBufOpts { name: string, exe: string?, places: ExePlace[], config_files: string[]?, filetypes: string[]? }
--- @alias FindExeForBufResult { name: string, file: string, exe: string, exe_path: string, place: ExePlace, config_file: string?, filetype: string? }
--- @param buf number
--- @param opts FindExeForBufOpts
--- @return FindExeForBufResult | nil
function M.find_exe_for_buf(buf, opts)
    local r = {} --- @type FindExeForBufResult
    r.name = opts.name
    r.file = vim.api.nvim_buf_get_name(buf)
    r.exe = opts.exe or opts.name

    if opts.filetypes then
        r.filetype = vim.api.nvim_get_option_value("filetype", { scope = "buffer", buf = buf })
        if not vim.tbl_contains(opts.filetypes, r.filetype) then return nil end
    end

    if opts.config_files then
        local config_file_list = vim.fs.find(opts.config_files, { path = r.file, upward = true })
        if #config_file_list == 0 then return nil end
        r.config_file = config_file_list[1]
    end

    local exe_path, place = M.find_exe(r.file, r.exe, opts.places)
    if exe_path == nil then return nil end
    r.exe_path = exe_path

    --- @cast place ExePlace
    r.place = place

    return r
end

return M
