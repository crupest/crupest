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

    vim.lsp.config("clangd", { cmd = { clangd } })

    vim.api.nvim_create_autocmd('LspAttach', {
        callback = function(ev)
            local client = vim.lsp.get_client_by_id(ev.data.client_id)
            if client and client.name == "clangd" then
                vim.keymap.set('n', 'grs', "<cmd>ClangdSwitchSourceHeader<cr>", {
                    buffer = ev.buf
                })
            end
        end
    })
end

local function setup_lua_ls()
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
                },
            },
        },
    })
end

local function setup()
    setup_clangd()
    setup_lua_ls()

    function _G.crupest_no_range_format()
        vim.notify("Range format is no supported by the lsp.", vim.log.levels.ERROR, {})
    end

    vim.api.nvim_create_autocmd('LspAttach', {
        callback = function(ev)
            local client = vim.lsp.get_client_by_id(ev.data.client_id)
            vim.keymap.set('n', 'gqa', vim.lsp.buf.format, { buffer = ev.buf })
            if client and not client:supports_method('textDocument/rangeFormatting') then
                vim.bo[ev.buf].formatexpr = "v:lua.crupest_no_range_format()"
            end
        end
    })

    vim.lsp.enable({ "clangd", "lua_ls", "denols" })
end

return {
    setup = setup
}
