local is_win = vim.fn.has("win32") ~= 0
local is_mac = vim.fn.has("mac") ~= 0

return {
    is_win = is_win,
    is_mac = is_mac
}
