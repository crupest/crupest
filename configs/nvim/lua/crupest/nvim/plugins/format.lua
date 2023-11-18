local find = require("crupest.system.find")
local constants = require("crupest.constants")

local function wrap_formatter_with_exe(name, exe)
    local formatter = require('formatter.defaults.' .. name)
    formatter = formatter()
    formatter.try_node_modules = false
    formatter.exe = exe
    return formatter
end

local function set_formatters_for_filetype(filetype, formatters)
    require('formatter.config').values.filetype[filetype] = formatters
end

local my_formatters = {
    {
        name = "prettier",
        exe_places = { "npm" },
        filetypes = constants.filetype_collections.frontend,
        config_files = constants.config_patterns.nodejs,
    },
}

local function find_custom_formatter(opts)
    if opts == nil then opts = {} end
    if opts.buf == nil then opts.buf = 0 end

    for _, f in ipairs(my_formatters) do
        local r = find.find_exe_for_buf(opts.buf, f)
        if r ~= nil then
            local formatter = wrap_formatter_with_exe(r.name, r.exe_path)
            set_formatters_for_filetype(r.filetype, { formatter })
            return r.name
        end
    end

    return nil
end


local function do_format(opt)
    if not opt then
        opt = {}
    end

    if not opt.buf then
        opt.buf = 0
    end

    local custom_formatter = find_custom_formatter(opt)

    if custom_formatter then
        print("Use custom formatters: " .. custom_formatter .. ".")
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

local function setup_format()
    require("formatter").setup {}
end

return {
    setup_format = setup_format,
    do_format = do_format,
}
