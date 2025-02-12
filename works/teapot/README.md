From https://github.com/qt/qtquick3d/tree/dev/examples/quick3d/view3d

This package only works on Ubuntu 22.04 because it relies on the system qt6 libs. At least I only test this platform. Other platforms might also work if the lib linkage is right. However, another way is to bundle all dependencies into the deb, which looks like most apps would do. But I'm new to deb package system and I'm in a hurry with no time to do more research.

In a word,

1. Make sure you are on Ubuntu 22.04.
2. Download `package.deb` from ci.
3. Run `sudo apt-get install package.deb` (NOT `dpkg`), and apt will take care of dependencies for you.
4. Run `crupest-teapot` and enjoy yourself!
