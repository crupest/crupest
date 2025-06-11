local function setup()
    require("conform").setup({
        formatters_by_ft = {
            javascript = { "prettierd", "prettier", stop_after_first = true },
            typescript = { "prettierd", "prettier", stop_after_first = true },
            javascriptreact = { "prettierd", "prettier", stop_after_first = true },
            typescriptreact = { "prettierd", "prettier", stop_after_first = true },
        },
        default_format_opts = {
            lsp_format = "fallback",
        },
    })
end

return {
    setup = setup
}
