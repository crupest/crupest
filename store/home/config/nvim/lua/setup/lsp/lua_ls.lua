local lspconfig = require("lspconfig")

local function setup()
    lspconfig.lua_ls.setup {
        settings = {
            Lua = {
                runtime = {
                    version = "LuaJIT"
                },
                diagnostics = {
                    globals = { "vim" },
                },
                workspace = {
                    library = {
                        [vim.fn.expand "$VIMRUNTIME/lua"] = true,
                        [vim.fn.expand "$VIMRUNTIME/lua/vim/lsp"] = true,
                        [vim.fn.stdpath "data" .. "/lazy/lazy.nvim/lua/lazy"] = true,
                    },
                    maxPreload = 100000,
                    preloadFileSize = 10000,
                },
            },
        },
    }
end

return {
    setup = setup
}
