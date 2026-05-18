local function setup()
    require("codecompanion").setup({
        interactions = {
            chat = {
                adapter = "deepseek",
                tools = {
                    opts = {
                        default_tools = {
                            "agent",
                        }
                    },
                }
            },
            inline = {
                adapter = "deepseek",
            },
            cmd = {
                adapter = "deepseek",
            },
            background = {
                adapter = "deepseek",
            },
        },
        adapters = {
            http = {
                deepseek = function()
                    return require("codecompanion.adapters").extend("deepseek", {
                        env = {
                            api_key = require('setup.credential').deepseek
                        },
                        schema = {
                            model = {
                                default = "deepseek-v4-pro"
                            },
                        },
                    })
                end,
            },
        },
        extensions = {
            history = {},
            spinner = {},
        }
    })
end

return {
    setup = setup
}
