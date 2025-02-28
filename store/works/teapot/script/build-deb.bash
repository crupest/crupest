set -e

mkdir -p build
pushd build
cmake .. "-DCMAKE_BUILD_TYPE=RelWithDebInfo"
make
mkdir -p package
cmake --install . --prefix ./package/
mkdir -p package/DEBIAN
cp ../debian/control ./package/DEBIAN/control
dpkg-deb --root-owner-group --build package
popd
