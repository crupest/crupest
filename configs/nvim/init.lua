-- disable netrw for nvim-tree
vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

vim.cmd([[
    let &shell = executable('pwsh') ? 'pwsh' : 'powershell'
    let &shellcmdflag = '-NoLogo -ExecutionPolicy RemoteSigned -Command [Console]::InputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();$PSDefaultParameterValues[''Out-File:Encoding'']=''utf8'';Remove-Alias -Force -ErrorAction SilentlyContinue tee;'
    let &shellredir = '2>&1 | %%{ "$_" } | Out-File %s; exit $LastExitCode'
    let &shellpipe  = '2>&1 | %%{ "$_" } | tee %s; exit $LastExitCode'
    set shellquote= shellxquote=
]])

vim.cmd.cd("~")

vim.opt.termguicolors = true;
vim.opt.fileformats = "unix,dos";
vim.opt.softtabstop = 4;
vim.opt.shiftwidth = 4;
vim.opt.expandtab = true;
vim.opt.wrap = false;
vim.opt.number = true;
vim.keymap.set('t', '<leader><esc>', [[<C-\><C-n>]])

if vim.g.neovide then
    vim.opt.guifont = "FiraCode Nerd Font";
    vim.g.neovide_transparency = 0.95;
    vim.g.neovide_input_ime = false;
    vim.g.neovide_cursor_vfx_mode = "ripple";
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

-- setup nvim-tree
require("nvim-tree").setup()

local nvim_tree_api = require("nvim-tree.api")
vim.keymap.set('n', '<leader>t', nvim_tree_api.tree.toggle, {})
vim.api.nvim_create_autocmd("DirChanged", {
    pattern = "global",
    callback = function(args)
        nvim_tree_api.tree.change_root(args.file)
    end
})

-- setup lualine
require('lualine').setup()

-- setup bufferline
require("bufferline").setup {
    options = {
        offsets = {
            {
                filetype = "NvimTree",
                text = "File Explorer",
                highlight = "Directory",
                separator = true
            }
        }
    }
}

-- setup gitsigns
require('gitsigns').setup()

-- setup toggleterm
require("toggleterm").setup {
    open_mapping = "<C-`>",
    start_in_insert = false,
}

-- setup autopairs
require("nvim-autopairs").setup {}

-- setup formatter
local prettier_formatter = function ()
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
local lint = require("lint")

local linter_eslint = require("lint.linters.eslint")
linter_eslint.cmd = function ()
    local current_buffer = vim.api.nvim_buf_get_name(0)
    return require("crupest.system").find_npm_exe(current_buffer, "eslint") or "eslint"
end
-- lint library use 'cmd /C' to run exe, but we don't need this, so explicitly
-- set args to empty.
linter_eslint.args = {}
linter_eslint.append_fname = true

lint.linters_by_ft = {
    javascript = { "eslint", "cspell" },
    javascriptreact = { "eslint", "cspell" },
    typescript = { "eslint", "cspell" },
    typescriptreact = { "eslint", "cspell" },
}

vim.api.nvim_create_autocmd({ "BufWritePost" }, {
    callback = function()
        lint.try_lint()
    end,
})

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
        ['<C-b>'] = cmp.mapping.scroll_docs(-4),
        ['<C-f>'] = cmp.mapping.scroll_docs(4),
        ['<C-Space>'] = cmp.mapping.complete(),
        ['<C-e>'] = cmp.mapping.abort(),
        ['<CR>'] = cmp.mapping.confirm({ select = true }), -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
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
lspconfig.cssls.setup {}
lspconfig.html.setup {}
lspconfig.tsserver.setup{
    on_new_config = function (new_config, new_root_dir)
        local local_tsserver = require("crupest-util").find_npm_exe(new_root_dir, "typescript-language-server");
        if local_tsserver then
            new_config.cmd = { local_tsserver, "--stdio" }
        end
    end,
}

-- setup trouble
require("trouble").setup()

-- setup keymap for telescope
local builtin = require('telescope.builtin')
vim.keymap.set('n', '<leader>f', builtin.find_files, {})
vim.keymap.set('n', '<leader>g', builtin.live_grep, {})
vim.keymap.set('n', '<leader>b', builtin.buffers, {})
vim.keymap.set('n', '<leader>h', builtin.help_tags, {})

-- setup keymap fnamemodifyfor lsp

-- Global mappings.
-- See `:help vim.diagnostic.*` for documentation on any of the below functions
vim.keymap.set('n', '<space>e', vim.diagnostic.open_float)
vim.keymap.set('n', '[d', vim.diagnostic.goto_prev)
vim.keymap.set('n', ']d', vim.diagnostic.goto_next)
vim.keymap.set('n', '<space>q', vim.diagnostic.setloclist)

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

require("catppuccin").setup{
    flavour = "mocha"
}

vim.cmd.colorscheme "catppuccin"

-- custom keymaps

vim.keymap.set("n", "<c-tab>", "<cmd>bnext<cr>")
vim.keymap.set("n", "<c-s-tab>", "<cmd>bNext<cr>")
vim.keymap.set("n", "<s-tab>", "<c-o>")
vim.keymap.set("n", "<c-q>", require("crupest.nvim").win_close_buf)
vim.keymap.set("n", "<esc>", require("crupest.nvim").close_float)

