local lint = require("lint")

local function run_lint()
    lint.try_lint()
    lint.try_lint("cspell")
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
        callback = run_lint,
    })
end

return {
    setup_lint = setup_lint,
    run_lint = run_lint
}

