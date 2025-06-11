--- spellchecker: words markdownlintrc

---@alias CruLinter { name: string, config_patterns: string[], filetypes: string[] | nil, fast: boolean }

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
    filetypes = { "markdown" },
    fast = true,
}

local linters = { cspell = cspell, markdownlint = markdownlint }

---@param linter CruLinter
---@param buf integer
---@return string | nil
local function find_config(linter, buf)
    local files = vim.fs.find(linter.config_patterns, {
        path = vim.api.nvim_buf_get_name(buf), upward = true })
    if #files ~= 0 then
        return files[1];
    end
    return nil
end

vim.list_extend(require("lint.linters.markdownlint").args, {
    "--config",
    function()
        return find_config(markdownlint, 0);
    end
})

---@param linter CruLinter
---@param buf integer
function vim.crupest.lint(linter, buf)
    if linter.filetypes then
        local filetype = vim.api.nvim_get_option_value("filetype", { buf = buf })
        if not vim.list_contains(linter.filetypes, filetype) then
            return
        end
    end

    if find_config(linter, buf) then
        require("lint").try_lint(linter.name)
    end
end

function vim.crupest.lint_all(buf, fast)
    for _, linter in pairs(linters) do
        if not fast or linter.fast then
            vim.crupest.lint(linter, buf)
        end
    end
end

local function setup()
    vim.api.nvim_create_autocmd(
        { "BufReadPost", "InsertLeave", "TextChanged" },
        {
            callback = function(opt)
                if vim.api.nvim_get_option_value("buftype", { buf = opt.buf }) == "" then
                    vim.crupest.lint_all(opt.buf, true)
                end
            end
        })
end

return {
    setup = setup,
}
