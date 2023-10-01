if not vim.uv then
    vim.uv = vim.loop
end

if vim.g.neovide then
    vim.opt.guifont = "CaskaydiaCove Nerd Font";
    vim.g.neovide_transparency = 0.98;
    vim.g.neovide_input_ime = false;
    vim.g.neovide_cursor_vfx_mode = "ripple";
end

local is_win = vim.fn.has("win32") ~= 0

if is_win then
    vim.cmd([[
    let &shell = executable('pwsh') ? 'pwsh' : 'powershell'
    let &shellcmdflag = '-NoLogo -ExecutionPolicy RemoteSigned -Command [Console]::InputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();$PSDefaultParameterValues[''Out-File:Encoding'']=''utf8'';Remove-Alias -Force -ErrorAction SilentlyContinue tee;'
    let &shellredir = '2>&1 | %%{ "$_" } | Out-File %s; exit $LastExitCode'
    let &shellpipe  = '2>&1 | %%{ "$_" } | tee %s; exit $LastExitCode'
    set shellquote= shellxquote=
]])
end

vim.cmd.cd("~")

vim.opt.termguicolors = true;
vim.opt.fileformats = "unix,dos";
vim.opt.softtabstop = 4;
vim.opt.shiftwidth = 4;
vim.opt.expandtab = true;
vim.opt.wrap = false;
vim.opt.number = true;

if is_win then
    vim.opt.completeslash = 'slash'
end

-- Init lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.uv.fs_stat(lazypath) then
    vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable", -- latest stable release
        lazypath,
    })
end
vim.opt.rtp:prepend(lazypath)

-- Use lazy.nvim
require("lazy").setup("plugins")

vim.cmd("colorscheme everforest")

-- setup neo-tree
require("neo-tree").setup({
    filesystem = {
        filtered_items = {
            hide_dotfiles = true,
            hide_gitignored = true,
            hide_hidden = true, -- only works on Windows for hidden files/directories
        },
        use_libuv_file_watcher = true
    }
})

-- setup lualine
require('lualine').setup({
    options = {
        theme = "auto", -- Can also be "auto" to detect automatically.
    }
})

-- setup toggleterm
require("toggleterm").setup {
    open_mapping = "<C-`>",
    start_in_insert = false,
}

-- setup autopairs
require("nvim-autopairs").setup {}

-- setup formatter
local prettier_formatter = function()
    local current_buffer = vim.api.nvim_buf_get_name(0)
    local prettier_exe = require("crupest.system").find_npm_exe(current_buffer, "prettier") or "prettier"

    if vim.fn.has("win32") ~= 0 then
        local escape = require("crupest.system").escape_space
        current_buffer = escape(current_buffer)
        prettier_exe = escape(prettier_exe)
    end

    return {
        exe = prettier_exe,
        args = {
            "--stdin-filepath",
            current_buffer
        },
        stdin = true,
    }
end

require("formatter").setup {
    filetype = {
        html = {
            prettier_formatter
        },
        css = {
            prettier_formatter
        },
        javascript = {
            prettier_formatter
        },
        javascriptreact = {
            prettier_formatter
        },
        typescript = {
            prettier_formatter
        },
        typescriptreact = {
            prettier_formatter
        }
    }
}

-- setup lint
local lint = require("crupest.nvim.plugins.lint")
lint.setup_lint()

-- setup nvim-cmp
local cmp = require("cmp")

cmp.setup({
    snippet = {
        expand = function(args)
            require("luasnip").lsp_expand(args.body)
        end,
    },
    window = {
    },
    mapping = cmp.mapping.preset.insert({
        ['<C-j>'] = cmp.mapping.select_next_item(),
        ['<C-k>'] = cmp.mapping.select_prev_item(),
        ['<C-b>'] = cmp.mapping.scroll_docs(-4),
        ['<C-f>'] = cmp.mapping.scroll_docs(4),
        ['<C-Space>'] = cmp.mapping.complete(),
        ['<C-e>'] = cmp.mapping.abort(),
        ['<CR>'] = cmp.mapping.confirm({ select = true }), -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
        ['<tab>'] = cmp.mapping.confirm({ select = true })
    }),
    sources = cmp.config.sources({
        { name = 'nvim_lsp' },
        { name = 'luasnip' },
    }, {
        { name = 'buffer' },
    })
})

-- setup lsp
local capabilities = require("cmp_nvim_lsp").default_capabilities()
local lspconfig = require("lspconfig")

-- setup lsp clangd
lspconfig.clangd.setup {
    capabilities = capabilities
}

-- setup lsp lua
lspconfig.lua_ls.setup {
    capabilities = capabilities,
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
                    [vim.fn.stdpath "data" .. "/lazy/ui/nvchad_types"] = true,
                    [vim.fn.stdpath "data" .. "/lazy/lazy.nvim/lua/lazy"] = true,
                },
                maxPreload = 100000,
                preloadFileSize = 10000,
            },
        },
    },
}

-- setup lsp frontend
require("crupest.nvim.lsp.frontend").setup_lsp_frontend()

-- setup lsp csharp
require("crupest.nvim.lsp.csharp").setup_lsp_csharp()

-- Use LspAttach autocommand to only map the following keys
-- after the language server attaches to the current buffer
vim.api.nvim_create_autocmd('LspAttach', {
    group = vim.api.nvim_create_augroup('UserLspConfig', {}),
    callback = function(ev)
        -- Enable completion triggered by <c-x><c-o>
        vim.bo[ev.buf].omnifunc = 'v:lua.vim.lsp.omnifunc'

        -- Buffer local mappings.
        -- See `:help vim.lsp.*` for documentation on any of the below functions
        local opts = { buffer = ev.buf }
        vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
        vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
        vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
        vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
        vim.keymap.set('n', '<C-k>', vim.lsp.buf.signature_help, opts)
        vim.keymap.set('i', '<C-k>', vim.lsp.buf.signature_help, opts)
        vim.keymap.set('n', '<space>wa', vim.lsp.buf.add_workspace_folder, opts)
        vim.keymap.set('n', '<space>wr', vim.lsp.buf.remove_workspace_folder, opts)
        vim.keymap.set('n', '<space>wl', function()
            print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
        end, opts)
        vim.keymap.set('n', '<space>D', vim.lsp.buf.type_definition, opts)
        vim.keymap.set('n', '<space>rn', vim.lsp.buf.rename, opts)
        vim.keymap.set({ 'n', 'v' }, '<space>ca', vim.lsp.buf.code_action, opts)
        vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
        vim.keymap.set('n', '<space>f', function()
            vim.lsp.buf.format { async = true }
        end, opts)
    end,
})


-- For terminal emulator
vim.keymap.set('t', '<leader><esc>', [[<C-\><C-n>]])

-- setup keymap for telescope
local builtin = require('telescope.builtin')
vim.keymap.set('n', '<leader>f', builtin.find_files, {})
vim.keymap.set('n', '<leader>g', builtin.live_grep, {})
vim.keymap.set('n', '<leader>b', builtin.buffers, {})
vim.keymap.set('n', '<leader>h', builtin.help_tags, {})

-- setup ketmap for tree
vim.keymap.set('n', '<leader>t', "<cmd>Neotree toggle<cr>", {})

-- See `:help vim.diagnostic.*` for documentation on any of the below functions
vim.keymap.set('n', '<leader>le', vim.diagnostic.open_float)
vim.keymap.set('n', '<leader>l[', vim.diagnostic.goto_prev)
vim.keymap.set('n', '<leader>l]', vim.diagnostic.goto_next)
vim.keymap.set('n', '<leader>lt', vim.diagnostic.setloclist)
vim.keymap.set('n', '<leader>ll', lint.run_lint)


vim.keymap.set("n", "<c-tab>", "<cmd>bnext<cr>")
vim.keymap.set("n", "<c-s-tab>", "<cmd>bNext<cr>")
vim.keymap.set("n", "<s-tab>", "<c-o>")
vim.keymap.set("n", "<c-q>", require("crupest.nvim").win_close_buf)
vim.keymap.set("n", "<esc>", require("crupest.nvim").close_float)

require("crupest.nvim.fs").setup_filesystem_user_commands()
