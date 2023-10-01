local capabilities = require("cmp_nvim_lsp").default_capabilities()
local lspconfig = require("lspconfig")

local function setup_lsp_c()
    -- setup lsp clangd
    lspconfig.clangd.setup {
        capabilities = capabilities
    }
end

return {
    setup_lsp_c = setup_lsp_c
}
