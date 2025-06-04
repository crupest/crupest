-- spellchecker: words denols luals

vim.lsp.config("*", {
    capabilities = vim.tbl_extend("force",
        vim.lsp.protocol.make_client_capabilities(),
        require("cmp_nvim_lsp").default_capabilities()
    )
})

local function setup_clangd()
    local clangd = "clangd"
    local brew_clangd_path = "/usr/local/opt/llvm/bin/clangd"

    if vim.uv.fs_stat(brew_clangd_path) ~= nil then
        clangd = brew_clangd_path
    end

    vim.lsp.config("clangd", {
        cmd = { clangd }
    })
    local old_on_attach = vim.lsp.config.clangd.on_attach
    vim.lsp.config.clangd.on_attach = function(client, bufnr)
        if old_on_attach then old_on_attach(client, bufnr) end
        vim.keymap.set('n', 'grs', "<cmd>ClangdSwitchSourceHeader<cr>", {
            buffer = bufnr
        })
    end
end

local function setup_luals()
    vim.lsp.config("lua_ls", {
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
    })
end

local function setup()
    vim.lsp.enable('denols')
    vim.lsp.enable('cmake')
    vim.lsp.enable('bashls')
    vim.lsp.enable('html')
    vim.lsp.enable('cssls')
    setup_clangd()
    setup_luals()
end


return {
    setup = setup
}
