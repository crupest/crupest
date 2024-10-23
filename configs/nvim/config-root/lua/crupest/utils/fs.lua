local is_win = vim.fn.has("win32") ~= 0

local function clean_path(path)
    if path == "/" then return path end
    path = string.gsub(path, "[/\\]+", "/")
    if string.sub(path, string.len(path)) == '/' then
        path = string.sub(path, 1, string.len(path) - 1)
    end
    return path
end

local function full_path(name)
    if is_win and string.match(name, "^[a-zA-Z]:[/\\]?$") then return clean_path(name) end
    local path = vim.fn.fnamemodify(name, ":p")
    return clean_path(path)
end

local function escape_space(str)
    return (string.gsub(str, " ", "\\ "))
end

local function path_get_dir(path)
    return full_path(vim.fn.fnamemodify(clean_path(path), ":h"))
end

local function walk_up(path, func)
    local current_path = full_path(path)
    while true do
        local result = func(current_path)
        if result ~= nil then
            return result
        end
        local new_path = path_get_dir(current_path)
        if new_path == current_path then
            break
        end
        current_path = new_path
    end
    return nil
end

local function exist(path)
    return vim.uv.fs_stat(path)
end

local function isfile(path)
    local s = vim.uv.fs_stat(path)
    if not s then return false end
    return s.type == "file"
end

local function isdir(path)
    local s = vim.uv.fs_stat(path)
    if not s then return false end
    return s.type == "directory"
end

local function mkdir(dir)
    local parents = {}

    walk_up(dir, function(p)
        table.insert(parents, 1, p)
    end)

    for _, v in ipairs(parents) do
        if exist(v) and not isdir(v) then
            vim.notify(v .. " is not a dir. Can't make dir " .. dir, vim.log.levels.ERROR)
            return
        end
        if not exist(v) then
            vim.notify("Creating dir " .. v)
            assert(vim.uv.fs_mkdir(v, 504)) -- mode = 0770
        end
    end
end

local function copy(old, new)
    mkdir(path_get_dir(new))
    assert(vim.uv.fs_copyfile(old, new))
end

local function remove(path)
    assert(vim.uv.fs_unlink(path))
end

local function move(old, new)
    mkdir(path_get_dir(new))
    assert(vim.uv.fs_rename(old, new))
end

return {
    clean_path = clean_path,
    full_path = full_path,
    escape_space = escape_space,
    path_get_dir = path_get_dir,
    walk_up = walk_up,
    exist = exist,
    isfile = isfile,
    isdir = isdir,
    mkdir = mkdir,
    copy = copy,
    remove = remove,
    move = move
}
