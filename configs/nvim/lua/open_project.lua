local a = require'plenary.async'
:with
local context_manager = require "plenary.context_manager"
local with = context_manager.with
local open = context_manager.open

local err, stat = a.fs_stat("./.project");
assert(not error, ".project file does not exist, you should run this script at project root.")

-- open nvim tree
local nvim_tree_api = require("nvim-tree.api")
nvim_tree_api.open()

-- open terminal
vim.cmd("split")
vim.cmd

