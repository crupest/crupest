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
            }
        },
        extensions = {
            mcphub = {
                callback = "mcphub.extensions.codecompanion",
                opts = {
                    -- MCP Tools
                    make_tools = true,                    -- Make individual tools (@server__tool) and server groups (@server) from MCP servers
                    show_server_tools_in_chat = true,     -- Show individual tools in chat completion (when make_tools=true)
                    add_mcp_prefix_to_tool_names = false, -- Add mcp__ prefix (e.g `@mcp__github`, `@mcp__neovim__list_issues`)
                    show_result_in_chat = true,           -- Show tool results directly in chat buffer
                    format_tool = nil,                    -- function(tool_name:string, tool: CodeCompanion.Agent.Tool) : string Function to format tool names to show in the chat buffer
                    -- MCP Resources
                    make_vars = false,                    -- Convert MCP resources to #variables for prompts
                    -- MCP Prompts
                    make_slash_commands = true,           -- Add MCP prompts as /slash commands
                }
            },
            history = {
            },
        }
    })
end

return {
    setup = setup
}
