export CODE_SERVER_CONFIG="/data/code-server-config.yaml"

CODE_SERVER_PROGRAM=code-server
CODE_SERVER_PORT=8080

if which "$CODE_SERVER_PROGRAM" > /dev/null 2>&1; then
    if ! pgrep -f "$CODE_SERVER_PROGRAM" > /dev/null 2>&1; then
        mkdir -p ~/.local/share/code-server
        nohup "$CODE_SERVER_PROGRAM" "--bind-addr", "0.0.0.0:$CODE_SERVER_PORT" \
            > ~/.local/share/code-server/log  2> ~/.local/share/code-server/error &
    fi
fi
