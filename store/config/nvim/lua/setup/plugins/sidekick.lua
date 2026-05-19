local function setup()
    require("sidekick").setup {}

    vim.keymap.set("n", "<tab>",
        function()
            if not require("sidekick").nes_jump_or_apply() then
                return "<Tab>"
            end
        end, { expr = true })
    vim.keymap.set({ "n", "t", "i", "x" }, "<c-.>",
        function() require("sidekick.cli").focus() end)
    vim.keymap.set("n", "<leader>aa",
        function() require("sidekick.cli").toggle() end)
    vim.keymap.set("n", "<leader>as",
        function() require("sidekick.cli").select({ filter = { installed = true } }) end)
    vim.keymap.set("n", "<leader>ad",
        function() require("sidekick.cli").close() end)
    vim.keymap.set({ "x", "n" }, "<leader>at",
        function() require("sidekick.cli").send({ msg = "{this}" }) end)
    vim.keymap.set("n", "<leader>af",
        function() require("sidekick.cli").send({ msg = "{file}" }) end)
    vim.keymap.set("x", "<leader>av",
        function() require("sidekick.cli").send({ msg = "{selection}" }) end)
    vim.keymap.set({ "n", "x" }, "<leader>ap",
        function() require("sidekick.cli").prompt() end)
    vim.keymap.set("n", "<leader>ac",
        function() require("sidekick.cli").toggle({ name = "claude", focus = true }) end)
end

return {
    setup = setup
}
