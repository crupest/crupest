append-bash-profile() {
    cat "/bootstrap/bash-profile/$1" >> /root/.bash_profile
}

copy-home-dot-file() {
    cp "/bootstrap/home-dot/$1" "/root/.$1"
}
