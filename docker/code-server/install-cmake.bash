CMAKE_VERSION=$(curl -s https://api.github.com/repos/Kitware/CMake/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
wget -O cmake-installer.sh https://github.com/Kitware/CMake/releases/download/v"$CMAKE_VERSION"/cmake-"$CMAKE_VERSION"-linux-x86_64.sh
chmod +x cmake-installer.sh
./cmake-installer.sh --skip-license --prefix=/usr
rm cmake-installer.sh
