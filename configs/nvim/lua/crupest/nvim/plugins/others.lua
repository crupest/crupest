local function setup()
    require("neo-tree").setup {
        filesystem = {
            filtered_items = {
                hide_dotfiles = false,
                hide_gitignored = false,
                hide_hidden = false, -- only works on Windows for hidden files/directories
            },
            use_libuv_file_watcher = true
        }
    }

    require('lualine').setup {}

    require("nvim-autopairs").setup {}
end

return {
    setup = setup
}
