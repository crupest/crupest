local config_patterns = {
    cspell = {
        ".cspell.json",
        "cspell.json",
        ".cSpell.json",
        "cSpell.json",
        "cspell.config.js",
        "cspell.config.cjs",
        "cspell.config.json",
        "cspell.config.yaml",
        "cspell.config.yml",
        "cspell.yaml",
        "cspell.yml",
    },
    nodejs = {
        "package.json"
    },
    deno = {
        "deno.json", "deno.jsonc"
    }
}

local filetypes = {
    js_ts = { 'javascript', 'javascriptreact', 'typescript', 'typescriptreact' }

}

return {
    config_patterns = config_patterns,
    filetypes = filetypes,
}
