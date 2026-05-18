local has_setup = false

local function setup()
    if has_setup then return end

    require 'nvim-treesitter.configs'.setup {
        highlight = { enable = true },
        incremental_selection = { enable = true },
        textobjects = { enable = true },
    }

    has_setup = true
end

return {
    setup = setup
}
