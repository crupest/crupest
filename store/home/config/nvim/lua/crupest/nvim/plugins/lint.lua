local lint = require("lint")

local find = require('crupest.utils.find')
local is_win = vim.fn.has("win32") ~= 0

local cspell_config_patterns = {
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

--- @type FindExeForBufOpts[]
local my_linters = {
    {
        name = "cspell",
        places = { "node_modules", "global" },
        config_files = cspell_config_patterns,
    },
}

local function run(opt)
    if not opt then
        opt = {}
    end

    if not opt.buf then
        opt.buf = 0
    end

    local linters = {}

    for _, l in ipairs(my_linters) do
        local linter = find.find_exe_for_buf(opt.buf, l)
        if linter then table.insert(linters, linter) end
    end


    local linter_names = {}

    for _, linter in ipairs(linters) do
        table.insert(linter_names, linter.name)
        require('lint.linters.' .. linter.name).cmd = linter.exe_path
        vim.diagnostic.config({ virtual_text = true }, lint.get_namespace(linter.name))
    end

    lint.try_lint(linter_names)
end

local function setup()
    if is_win then
        for _, l in ipairs(my_linters) do
            local name = l.name
            local linter = require('lint.linters.' .. name)
            if linter.cmd == 'cmd.exe' then
                linter.cmd = linter.args[2]
            end
            table.remove(linter.args, 1)
            table.remove(linter.args, 1)
        end
    end

    vim.api.nvim_create_autocmd({ "BufWritePost" }, {
        callback = function(opt)
            run({
                buf = opt.buffer
            })
        end,
    })

    vim.keymap.set('n', '<leader>lr', run)
end

return {
    setup = setup,
}
