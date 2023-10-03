local fs = require("crupest.system.fs")
local find_npm_exe = require("crupest.system.find").find_npm_exe;

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

local formatters_for_filetype = {
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

local function get_formatter_name(formatter)
    if formatter == prettier_formatter then return "prettier" end
    return nil
end

local function get_formatter_name_list(formatters)
    local result = {}
    for _, formatter in ipairs(formatters) do
        table.insert(result, get_formatter_name(formatter))
    end
    return result
end

local function setup_formatter()
    require("formatter").setup {
        filetype = formatters_for_filetype
    }
end


local function get_custom_formatters(bufnr)
    local filetype = vim.api.nvim_buf_get_option(bufnr, "filetype")
    for ft, formatters in pairs(formatters_for_filetype) do
        if filetype == ft then
            return true, get_formatter_name_list(formatters)
        end
    end
    return false, {}
end

local function run_formatter(opt)
    if not opt then
        opt = {}
    end

    if not opt.buf then
        opt.buf = 0
    end

    local has_custom_formatter, formatter_names = get_custom_formatters(opt.buf)

    local formatter_name_str = ""
    for i, name in ipairs(formatter_names) do
        if i == 1 then
            formatter_name_str = name
        else
            formatter_name_str = formatter_name_str .. " " .. name
        end
    end

    if has_custom_formatter then
        print("Use custom formatters: " .. formatter_name_str .. ".")
        vim.cmd("Format")
        return
    end

    local has_lsp = vim.lsp.get_active_clients({ bufnr = 0 })
    if has_lsp then
        print("Use lsp formatter.")
        vim.lsp.buf.format { async = true }
        return
    end

    vim.notify("No formatters found.", vim.log.levels.ERROR);
end

return {
    setup_formatter = setup_formatter,
    run_formatter = run_formatter
}
