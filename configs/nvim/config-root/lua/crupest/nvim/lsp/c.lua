local lspconfig = require("lspconfig")
local capabilities = require("cmp_nvim_lsp").default_capabilities()

local get_exe = require("crupest.utils.find").get_exe

local brew_clangd_path = "/usr/local/opt/llvm/bin/clangd"

local function setup()
    local clangd = "clangd"

    if get_exe(brew_clangd_path) then
        clangd = brew_clangd_path
    end

    -- setup lsp clangd
    lspconfig.clangd.setup {
        cmd = { clangd },
        capabilities = capabilities,
        on_attach = function(_, bufnr)
            vim.keymap.set('n', '<space>s', "<cmd>ClangdSwitchSourceHeader<cr>", {
                buffer = bufnr
            })
        end
    }
end

return {
    setup = setup
}
