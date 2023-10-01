local function setup_filesystem_user_commands()
    vim.api.nvim_create_user_command("Mv", function(opts)
        require("crupest.nvim").mv_buf_file(vim.api.nvim_get_current_buf(), opts.fargs[1])
    end, {
        nargs = 1,
        complete = "file"
    })

    vim.api.nvim_create_user_command("MvFile", function(opts)
        if (#opts.fargs ~= 2) then
            vim.notify("MvFile accepts exactly two arguments, old file and new file.")
        end
        require("crupest.nvim").mv_file(opts.fargs[1], opts.fargs[2])
    end, {
        nargs = "+",
        complete = "file"
    })

    vim.api.nvim_create_user_command("MvDir", function(opts)
        if (#opts.fargs ~= 2) then
            vim.notify("MvDir accepts exactly two arguments, old dir and new dir.")
        end
        require("crupest.nvim").mv_dir(opts.fargs[1], opts.fargs[2])
    end, {
        nargs = "+",
        complete = "file"
    })

    vim.api.nvim_create_user_command("Rename", function(opts)
        require("crupest.nvim").rename_buf_file(vim.api.nvim_get_current_buf(), opts.fargs[1])
    end, {
        nargs = 1,
        complete = "file"
    })

    vim.api.nvim_create_user_command("RenameFile", function(opts)
        if (#opts.fargs ~= 2) then
            vim.notify("RenameFile accepts exactly two arguments, old file and new file.")
        end
        require("crupest.nvim").rename_file(opts.fargs[1], opts.fargs[2])
    end, {
        nargs = "+",
        complete = "file"
    })
end

return {
    setup_filesystem_user_commands = setup_filesystem_user_commands
}
