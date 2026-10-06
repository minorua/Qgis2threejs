# Install three.js package and copy un-minified library files.
#

echo
printf "* Install npm dependencies? [y/N] "
read -r answer

if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
  npm install
else
  echo "Skipping npm install."
fi

echo
echo "* Replace the bundled three.js files with the un-minified versions"

THREE_BUILD=node_modules/three/build
TARGET_DIR=web/js/lib/three

(
  set -x
  cp "$THREE_BUILD/three.core.js" "$TARGET_DIR"
  cp "$THREE_BUILD/three.module.js" "$TARGET_DIR"
)

echo Completed.
