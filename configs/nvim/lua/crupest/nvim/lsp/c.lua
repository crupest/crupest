local lspconfig = require("lspconfig")
local capabilities = require("cmp_nvim_lsp").default_capabilities()

local function setup_lsp_c()
    -- setup lsp clangd
    lspconfig.clangd.setup {
        capabilities = capabilities,
        on_attach = function(_, bufnr)
            vim.keymap.set('n', '<space>s', "<cmd>ClangdSwitchSourceHeader<cr>", {
                buffer = bufnr
            })
        end
    }
end

return {
    setup_lsp_c = setup_lsp_c
}
