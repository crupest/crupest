if not vim.uv then
    vim.uv = vim.loop
end

if vim.g.neovide then
    -- spellchecker: disable-next-line
    vim.opt.guifont = "FiraCode Nerd Font";
    vim.g.neovide_transparency = 0.98;
    vim.g.neovide_input_ime = false;
    vim.g.neovide_cursor_vfx_mode = "ripple";
end

local is_win = vim.fn.has("win32") ~= 0

-- spellchecker: disable
if is_win then
    vim.cmd([[
    let &shell = executable('pwsh') ? 'pwsh' : 'powershell'
    let &shellcmdflag = '-NoLogo -ExecutionPolicy RemoteSigned -Command [Console]::InputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();$PSDefaultParameterValues[''Out-File:Encoding'']=''utf8'';Remove-Alias -Force -ErrorAction SilentlyContinue tee;'
    let &shellredir = '2>&1 | %%{ "$_" } | Out-File %s; exit $LastExitCode'
    let &shellpipe  = '2>&1 | %%{ "$_" } | tee %s; exit $LastExitCode'
    set shellquote= shellxquote=
    ]])
else
    vim.cmd([[
    let &shell='bash --login'
    ]])
end
-- spellchecker: enable

-- spellchecker: disable
vim.opt.termguicolors = true;
vim.opt.fileformats = "unix,dos";
vim.opt.softtabstop = 4;
vim.opt.shiftwidth = 4;
vim.opt.expandtab = true;
vim.opt.wrap = false;
vim.opt.number = true;
-- spellchecker: enable

if is_win then
    -- spellchecker: disable-next-line
    vim.opt.completeslash = 'slash'
end

-- Init lazy.nvim
local lazy_path = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.uv.fs_stat(lazy_path) then
    vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable", -- latest stable release
        lazy_path,
    })
end
vim.opt.rtp:prepend(lazy_path)

-- Use lazy.nvim
require("lazy").setup("plugins")

vim.cmd("colorscheme everforest")

-- setup neo-tree
require("neo-tree").setup({
    filesystem = {
        filtered_items = {
            hide_dotfiles = false,
            hide_gitignored = false,
            hide_hidden = false, -- only works on Windows for hidden files/directories
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

-- setup gitsigns
require('gitsigns').setup()

-- setup comment
require('Comment').setup()

-- setup format
local format = require("crupest.nvim.plugins.format")
format.setup_format()

-- setup lint
local lint = require("crupest.nvim.plugins.lint")
lint.setup_lint()

-- setup nvim-cmp
local snip = require("crupest.nvim.plugins.snip")
local luasnip = snip.luasnip
snip.setup_snip()

local cmp = require("cmp")

cmp.setup({
    snippet = {
        expand = function(args)
            luasnip.lsp_expand(args.body)
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
        ['<C-y>'] = cmp.mapping.confirm({ select = true })
    }),
    sources = cmp.config.sources({
        { name = 'nvim_lsp' },
        { name = 'luasnip' },
    }, {
        { name = 'buffer' },
    })
})


require("crupest.nvim.lsp.c").setup_lsp_c()
require("crupest.nvim.lsp.lua").setup_lsp_lua()
require("crupest.nvim.lsp.deno").setup_lsp_deno()
require("crupest.nvim.lsp.frontend").setup_lsp_frontend()
require("crupest.nvim.lsp.csharp").setup_lsp_csharp()
-- There is some problem of rust analyzer.
-- require("crupest.nvim.lsp.rust").setup_lsp_rust()

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

        vim.keymap.set('n', '<space>f', format.do_format, opts)
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

-- setup keymap for tree
vim.keymap.set('n', '<leader>t', "<cmd>Neotree toggle<cr>", {})

-- See `:help vim.diagnostic.*` for documentation on any of the below functions
vim.keymap.set('n', '<leader>le', vim.diagnostic.open_float)
vim.keymap.set('n', '<leader>l[', vim.diagnostic.goto_prev)
vim.keymap.set('n', '<leader>l]', vim.diagnostic.goto_next)
vim.keymap.set('n', '<leader>ll', vim.diagnostic.setloclist)
vim.keymap.set('n', '<leader>lr', lint.run_lint)

vim.keymap.set("n", "<c-tab>", "<cmd>bnext<cr>")
vim.keymap.set("n", "<c-s-tab>", "<cmd>bNext<cr>")
vim.keymap.set("n", "<s-tab>", "<c-o>")
vim.keymap.set("n", "<c-q>", require("crupest.nvim").win_close_buf)
vim.keymap.set("n", "<esc>", require("crupest.nvim").close_float)

require("crupest.nvim.fs").setup_filesystem_user_commands()
