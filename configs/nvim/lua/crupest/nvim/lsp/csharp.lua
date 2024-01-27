local lspconfig = require("lspconfig");
local capabilities = require("cmp_nvim_lsp").default_capabilities()


local function setup_lsp_csharp()
    lspconfig.csharp_ls.setup {
        capabilities = capabilities,
        root_dir = lspconfig.util.root_pattern("*.csproj"),
    }
end

return {
    setup_lsp_csharp = setup_lsp_csharp
}
