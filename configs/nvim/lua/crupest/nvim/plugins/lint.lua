local lint = require("lint")
local find = require('crupest.system.find')
local constants = require("crupest.constants")


local my_linters = {
    {
        name = "cspell",
        exe_places = { "npm", "global" },
        config_files = constants.config_patterns.cspell,
    },
    {
        name = "eslint",
        exe_places = { "npm" },
        filetypes = constants.filetypes.js_ts,
        config_files = { "package.json" }
    },
    {
        name = "deno",
        exe_places = { "global" },
        filetypes = constants.filetypes.js_ts,
        config_files = { "deno.json", "deno.jsonc" }
    }
}

local function run_lint(opt)
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
    end

    lint.try_lint(linter_names)
end

local function setup_lint()
    if require('crupest.system').is_win then
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
            run_lint({
                buf = opt.buffer
            })
        end,
    })
end

return {
    setup_lint = setup_lint,
    run_lint = run_lint
}
