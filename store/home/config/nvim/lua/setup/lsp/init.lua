local lspconfig = require("lspconfig")
local cmp_nvim_lsp = require("cmp_nvim_lsp")
local cmp_default_caps = cmp_nvim_lsp.default_capabilities()

local lspconfig_default_caps = lspconfig.util.default_config.capabilities

lspconfig.util.default_config = vim.tbl_extend(
    "force",
    lspconfig.util.default_config,
    {
        capabilities = vim.tbl_extend("force",  lspconfig_default_caps, cmp_default_caps),
        autostart = false,
    })

local function setup()
    lspconfig.cmake.setup {}
    lspconfig.bashls.setup {}
    require("setup.lsp.clangd").setup()
    require("setup.lsp.lua_ls").setup()
end


return {
    setup = setup
}
