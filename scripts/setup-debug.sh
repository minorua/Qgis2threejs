# Install three.js package and copy un-minified library files.
#
#   begin: 2026-07-09

echo
echo "* Install npm dependencies"

npm install

echo
echo "* Replace the bundled three.js files with the un-minified versions"

THREE_BUILD=node_modules/three/build
TARGET_DIR=web/js/lib/three

cp "$THREE_BUILD/three.core.js" "$TARGET_DIR"
cp "$THREE_BUILD/three.module.js" "$TARGET_DIR"
