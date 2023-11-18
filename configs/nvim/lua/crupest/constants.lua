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

local filetype_collections = {
    js_ts = { 'javascript', 'javascriptreact', 'typescript', 'typescriptreact' },
    html_css = { 'html', 'css' },
    frontend = { 'javascript', 'javascriptreact', 'typescript', 'typescriptreact', 'html', 'css' },
}

return {
    config_patterns = config_patterns,
    filetype_collections = filetype_collections,
}
