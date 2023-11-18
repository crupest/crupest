local luasnip = require("luasnip")

local ls = luasnip
-- some shorthands...
local s = ls.snippet
local sn = ls.snippet_node
local t = ls.text_node
local i = ls.insert_node
local f = ls.function_node
local c = ls.choice_node
local d = ls.dynamic_node
local r = ls.restore_node
local l = require("luasnip.extras").lambda
local rep = require("luasnip.extras").rep
local p = require("luasnip.extras").partial
local m = require("luasnip.extras").match
local n = require("luasnip.extras").nonempty
local dl = require("luasnip.extras").dynamic_lambda
local fmt = require("luasnip.extras.fmt").fmt
local fmta = require("luasnip.extras.fmt").fmta
local types = require("luasnip.util.types")
local conds = require("luasnip.extras.conditions")
local conds_expand = require("luasnip.extras.conditions.expand")

local function copy(args)
    return args[1]
end

local function setup_snip()
    vim.keymap.set({ "i", "s" }, "<C-L>", function() luasnip.jump(1) end, { silent = true })
    vim.keymap.set({ "i", "s" }, "<C-J>", function() luasnip.jump(-1) end, { silent = true })

    vim.keymap.set({ "i", "s" }, "<C-E>", function()
        if luasnip.choice_active() then
            luasnip.change_choice(1)
        end
    end, { silent = true })

    luasnip.add_snippets("cpp", {
        s("cs", {
            i(1, "classname"),
            t("::"),
            f(copy, 1),
            t("("),
            i(0),
            t(") { }")
        }),

        s("ds", {
            i(1, "classname"),
            t("::~"),
            f(copy, 1),
            t("() { }")
        }),

        s("csds", {
            i(1, "classname"),
            t("::"),
            f(copy, 1),
            t("("),
            i(0),
            t({ ") { }", "", "" }),
            f(copy, 1),
            t("::~"),
            f(copy, 1),
            t("() { }")
        }),
    })
end

return {
    setup_snip = setup_snip,
    luasnip = luasnip
}
