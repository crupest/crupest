local lint = require("lint")

local cspell = {
    name = "cspell",
    config_patterns = {
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
    },
    fast = true,
}

local markdownlint = {
    name = "markdownlint",
    config_patterns = {
        ".markdownlint.jsonc",
        ".markdownlint.json",
        ".markdownlint.yaml",
        ".markdownlint.yml",
        ".markdownlintrc",
    },
    fast = true,
}

local linters = { cspell, markdownlint }

local linter_names = vim.tbl_map(function(l) return l.name end, linters)

local function cru_lint(linter, opt)
    opt = opt or {}

    if not opt.buf then
        opt.buf = 0
    end

    if 0 ~= #vim.fs.find(linter.config_patterns, {
            path = vim.api.nvim_buf_get_name(opt.buf), upward = true }) then
        lint.try_lint(linter.name)
    end
end

local function cru_lint_one(name, opt)
    for _, linter in ipairs(linters) do
        if linter.name == name then
            cru_lint(linter, opt)
            return
        end
    end
    vim.notify("No linter named " .. name .. " is configured.", vim.log.levels.ERROR, {})
end

local function cru_lint_all(opt, fast)
    for _, linter in ipairs(linters) do
        if not fast or linter.fast then
            cru_lint(linter, opt)
        end
    end
end

local function cru_lint_all_fast(opt)
    local buf = opt.buf
    if vim.api.nvim_get_option_value("buftype", { buf = buf }) == "" then
        cru_lint_all(opt, true)
    end
end

local function setup()
    vim.api.nvim_create_autocmd({ "BufReadPost", "InsertLeave", "TextChanged" }, { callback = cru_lint_all_fast })

    local function cru_lint_cmd(opt)
        if #opt.args == 0 then
            cru_lint_all(opt, false)
        else
            cru_lint_one(opt.args, opt)
        end
    end

    vim.api.nvim_create_user_command("CruLint", cru_lint_cmd,
        { nargs = '?', complete = function() return linter_names end })
end

return {
    setup = setup,
}
