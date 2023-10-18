local lspconfig = require("lspconfig")
local capabilities = require("cmp_nvim_lsp").default_capabilities()


local function setup_lsp_rust()
    lspconfig.rust_analyzer.setup {
        capabilities = capabilities,
    }
end

return {
    setup_lsp_rust = setup_lsp_rust
}
