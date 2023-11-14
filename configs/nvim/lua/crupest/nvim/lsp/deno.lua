local lspconfig = require("lspconfig");
local capabilities = require("cmp_nvim_lsp").default_capabilities()

local function setup_lsp_deno()
    lspconfig.denols.setup {
        capabilities = capabilities,
        root_dir = lspconfig.util.root_pattern("deno.json", "deno.jsonc"),
    }
end

return {
    setup_lsp_deno = setup_lsp_deno
}
