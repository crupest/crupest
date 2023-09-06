vim.cmd.cd("~");
vim.opt.shell = "pwsh";

vim.opt.softtabstop = 4;
vim.opt.shiftwidth = 4;
vim.opt.expandtab = true;

if vim.g.neovide then
    vim.g.neovide_transparency = 0.95;
    vim.g.neovide_input_ime = false;
    vim.g.neovide_cursor_vfx_mode = "railgun";
end

