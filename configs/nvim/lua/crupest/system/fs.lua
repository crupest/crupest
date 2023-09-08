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
    require("crupest/system").walk_up(dir, function(p)
        table.insert(parents, 1, p)
    end)

    for _, v in ipairs(parents) do
        if exist(v) and not isdir(v) then
            vim.notify(v.." is not a dir. Can't make dir "..dir, vim.log.levels.ERROR)
            return
        end
        if not exist(v) then
            vim.notify("Creating dir "..v)
            assert(vim.uv.fs_mkdir(v, 504)) -- mode = 0770
        end
    end
end

local function copy(old, new)
    mkdir(vim.fn.fnamemodify(new, ":p:h"))
    assert(vim.uv.fs_copyfile(old, new))
end

local function remove(path)
    assert(vim.uv.fs_unlink(path))
end

local function move(old, new)
    mkdir(vim.fn.fnamemodify(new, ":p:h"))
    assert(vim.uv.fs_rename(old, new))
end

return {
    exist = exist,
    isfile = isfile,
    isdir = isdir,
    mkdir = mkdir,
    copy = copy,
    remove = remove,
    move = move
}

