-- spellchecker: disable
return {
    { "catppuccin/nvim", name = "catppuccin", priority = 1000 },
    "neovim/nvim-lspconfig",
    "hrsh7th/nvim-cmp",
    "hrsh7th/cmp-nvim-lsp",
    "hrsh7th/cmp-buffer",
    "hrsh7th/cmp-path",
    {
        "nvim-treesitter/nvim-treesitter",
        build = ":TSUpdate"
    },
    {
        "nvim-neo-tree/neo-tree.nvim",
        branch = "v3.x",
        dependencies = {
            "nvim-lua/plenary.nvim",
            "nvim-tree/nvim-web-devicons", -- not strictly required, but recommended
            "MunifTanjim/nui.nvim",
            -- {"3rd/image.nvim", opts = {}}, -- Optional image support in preview window: See `# Preview Mode` for more information
        },
        lazy = false, -- neo-tree will lazily load itself
    },
    {
        "nvim-lualine/lualine.nvim",
        dependencies = { 'nvim-tree/nvim-web-devicons' }
    },
    {
        "nvim-telescope/telescope.nvim",
        dependencies = { 'nvim-lua/plenary.nvim' }
    },
    "windwp/nvim-autopairs",
    "mfussenegger/nvim-lint",
    "lewis6991/gitsigns.nvim",
}
