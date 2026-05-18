local moonshot_url = "https://api.moonshot.cn"
local kimi_model = "kimi-k2.6"

local url = moonshot_url
local model = kimi_model

local function setup()
    require("codecompanion").setup({
        interactions = {
            chat = {
                adapter = "openai_compatible",
            },
            inline = {
                adapter = "openai_compatible",
            },
            cmd = {
                adapter = "openai_compatible",
            },
            background = {
                adapter = "openai_compatible",
            },
        },
        adapters = {
            http = {
                openai_compatible = function()
                    return require("codecompanion.adapters").extend("openai_compatible", {
                        env = {
                            url = url,
                            api_key = "OPENAI_API_KEY",
                        },
                        schema = {
                            model = {
                                default = model
                            },
                        },
                    })
                end
            },
        },
        extensions = {
            history = {
                opts = {
                    -- auto_generate_title = false,
                }
            },
        }
    })
end

return {
    setup = setup
}
