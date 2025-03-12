local lspconfig = require("lspconfig")

local brew_clangd_path = "/usr/local/opt/llvm/bin/clangd"

local function setup()
    local clangd = "clangd"

    if vim.uv.fs_stat(brew_clangd_path) ~= nil then
        clangd = brew_clangd_path
    end

    -- setup lsp clangd
    lspconfig.clangd.setup {
        cmd = { clangd },
        on_attach = function(_, bufnr)
            vim.keymap.set('n', 'grs', "<cmd>ClangdSwitchSourceHeader<cr>", {
                buffer = bufnr
            })
        end
    }
end

return {
    setup = setup
}
