local lspconfig = require("lspconfig")
local capabilities = require("cmp_nvim_lsp").default_capabilities()

local function setup()
    lspconfig.bashls.setup {
        capabilities = capabilities,
    }
end

return {
    setup = setup
}
