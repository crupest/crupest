local fs = require("crupest.system.fs")
local find_npm_exe = require("crupest.system.find").find_npm_exe;

local function setup_formatter()
    local prettier_formatter = function()
        local current_buffer = vim.api.nvim_buf_get_name(0)
        local prettier_exe = find_npm_exe(current_buffer, "prettier") or "prettier"

        if vim.fn.has("win32") ~= 0 then
            local escape = fs.escape_space
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
end

return {
    setup_formatter = setup_formatter
}
