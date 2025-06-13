vim.lsp.config("*", {
    capabilities = vim.tbl_extend("force",
        vim.lsp.protocol.make_client_capabilities(),
        require("cmp_nvim_lsp").default_capabilities()
    )
})

---@param ev vim.api.keyset.create_autocmd.callback_args
---@param name string
local function client_name_is(ev, name)
    local client = vim.lsp.get_client_by_id(ev.data.client_id)
    return client and client.name == name
end

local function setup_clangd()
    local clangd = "clangd"
    local brew_clangd_path = "/usr/local/opt/llvm/bin/clangd"

    if vim.uv.fs_stat(brew_clangd_path) ~= nil then
        clangd = brew_clangd_path
    end

    vim.lsp.config("clangd", { cmd = { clangd } })

    vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(ev)
            if client_name_is(ev, "clangd") then
                vim.keymap.set("n", "grs", "<cmd>ClangdSwitchSourceHeader<cr>", {
                    buffer = ev.buf
                })
            end
        end
    })

    vim.api.nvim_create_autocmd("LspDetach", {
        callback = function(ev)
            if client_name_is(ev, "clangd") then
                vim.keymap.del("n", "grs", { buffer = ev.buf })
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

function vim.crupest.no_range_format()
    print("Lsp doesn't support range formatting. Use gqa to format the whole document.")
    return 0
end

local function setup_denols()
    vim.lsp.config("denols", {
        root_dir = function(bufnr, on_dir)
            local deno_configs = vim.fs.find({ "deno.json", "deno.jsonc" }, {
                path = vim.api.nvim_buf_get_name(bufnr), upward = true, limit = math.huge })
            if 0 ~= #deno_configs then
                local deno_config = deno_configs[#deno_configs]
                on_dir(vim.fs.dirname(deno_config))
            end
        end,
    })

    vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(ev)
            if client_name_is(ev, "denols") then
                vim.api.nvim_set_option_value(
                    "formatexpr",
                    "v:lua.vim.crupest.no_range_format()",
                    { buf = ev.buf }
                )
            end
        end
    })

    vim.api.nvim_create_autocmd("LspDetach", {
        callback = function(ev)
            if client_name_is(ev, "denols") then
                vim.api.nvim_set_option_value("formatexpr", "", { buf = ev.buf })
            end
        end
    })
end


local function setup()
    vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(ev)
            vim.keymap.set("n", "gqa", vim.lsp.buf.format, { buffer = ev.buf })
        end
    })

    vim.api.nvim_create_autocmd("LspDetach", {
        callback = function(ev)
            vim.keymap.del("n", "gqa", { buffer = ev.buf })
        end
    })

    setup_clangd()
    setup_lua_ls()
    setup_denols()
    vim.lsp.enable({ "clangd", "lua_ls", "denols" })
end

return {
    setup = setup
}
