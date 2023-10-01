local fs = require("crupest.system.fs")
local lint = require("lint")

local cspell_config_filenames = {
    ".cspell.json",
    "cspell.json",
    ".cSpell.json",
    "cSpell.json",
    "cspell.config.js",
    "cspell.config.cjs",
    "cspell.config.json",
    "cspell.config.yaml",
    "cspell.config.yml",
    "cspell.yaml",
    "cspell.yml",
}

local cspell_enable_dirs = {}

local function detect_cspell(file)
    for _, dir in ipairs(cspell_enable_dirs) do
        if string.find(fs.full_path(file), dir, 0, true) == 1 then
            return true
        end
    end
    return fs.walk_up(file, function(current_path)
        for _, name in ipairs(cspell_config_filenames) do
            local cspell_config_file = current_path .. "/" .. name
            if fs.isfile(cspell_config_file) then
                table.insert(cspell_enable_dirs, current_path)
                return true
            end
        end
        return nil
    end) or false
end

local function run_lint(opt)
    if not opt then
        opt = {}
    end

    if not opt.file then
        opt.file = vim.api.nvim_buf_get_name(0)
    end

    if opt.run_cspell == nil then
        opt.run_cspell = detect_cspell(opt.file)
    end

    lint.try_lint()

    if opt.run_cspell then
        lint.try_lint("cspell")
    end
end

local function setup_lint()
    local linter_eslint = require("lint.linters.eslint")

    linter_eslint.cmd = function()
        local current_buffer = vim.api.nvim_buf_get_name(0)
        return require("crupest.system").find_npm_exe(current_buffer, "eslint") or "eslint"
    end

    -- lint library use 'cmd /C' to run exe, but we don't need this, so explicitly
    -- set args to empty.
    linter_eslint.args = {}
    linter_eslint.append_fname = true

    lint.linters_by_ft = {
        javascript = { "eslint" },
        javascriptreact = { "eslint" },
        typescript = { "eslint" },
        typescriptreact = { "eslint" },
    }

    vim.api.nvim_create_autocmd({ "BufWritePost" }, {
        callback = function(opt)
            run_lint({
                file = opt.file
            })
        end,
    })
end

return {
    setup_lint = setup_lint,
    run_lint = run_lint
}
