-- spellchecker: disable
return {
    "neovim/nvim-lspconfig",
    "Hoffs/omnisharp-extended-lsp.nvim",
    "hrsh7th/nvim-cmp",
    "hrsh7th/cmp-nvim-lsp",
    "hrsh7th/cmp-buffer",
    "hrsh7th/cmp-path",
    "hrsh7th/cmp-cmdline",
    "L3MON4D3/LuaSnip",
    "saadparwaiz1/cmp_luasnip",
    {
        "sainnhe/everforest",
        lazy = false,
        priority = 1000, -- make sure to load this before all the other start plugins
    },
    "nvim-tree/nvim-web-devicons",
    "nvim-lua/plenary.nvim",
    "nvim-lualine/lualine.nvim",
    "nvim-telescope/telescope.nvim",
    "windwp/nvim-autopairs",
    "mhartington/formatter.nvim",
    "mfussenegger/nvim-lint",
    "akinsho/toggleterm.nvim",
    "lewis6991/gitsigns.nvim",
    "numToStr/Comment.nvim",
    {
        "nvim-neo-tree/neo-tree.nvim",
        dependencies = {
            "nvim-lua/plenary.nvim",
            "MunifTanjim/nui.nvim",
        },
    },
}
