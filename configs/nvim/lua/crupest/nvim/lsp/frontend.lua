local lspconfig = require("lspconfig");
local capabilities = require("cmp_nvim_lsp").default_capabilities()

local function setup_lsp_frontend()
    lspconfig.cssls.setup {
        capabilities = capabilities
    }

    lspconfig.html.setup {
        capabilities = capabilities
    }

    lspconfig.tsserver.setup {
        capabilities = capabilities,
        on_new_config = function(new_config, new_root_dir)
            local local_tsserver = require("crupest.system.find").find_npm_exe(new_root_dir, "typescript-language-server");
            if local_tsserver then
                new_config.cmd = { local_tsserver, "--stdio" }
            end
        end,
    }
end

return {
    setup_lsp_frontend = setup_lsp_frontend
}
