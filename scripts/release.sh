# Release script for plugin
#   begin: 2013-12-02

export PATH=$PATH:/c/OSGeo4W/bin

PLUGINNAME=Qgis2threejs

JS_FILES="\
web/js/dist/Qgis2threejs.js
web/js/dist/gui_dat.js
web/js/dist/preview.js
web/js/dist/browserbridge.js"

echo "============================================================"
echo " Release process started: ${PLUGINNAME}"
echo "============================================================"

echo
echo "== Cleaning up =="

echo "Removing Python bytecode files..."
rm -f -r *.pyc

echo "Removing previous release archive..."
rm -f "${PLUGINNAME}.zip"

echo "Removing previously generated JavaScript bundle..."
rm -f $JS_FILES

echo
echo "== Version check =="

metadata_version=$(sed -nE 's/^version=(.+)$/\1/p' metadata.txt)
web_version=$(sed -nE 's/^export const VERSION = "([^"]+)";$/\1/p' web/src/Qgis2threejs.ts)
conf_version=$(sed -nE 's/^PLUGIN_VERSION = "([^"]+)"$/\1/p' conf.py)
conf_version_int=$(sed -nE 's/^PLUGIN_VERSION_INT = ([0-9]+)$/\1/p' conf.py)

if [ -z "$web_version" ] || [ -z "$conf_version" ] || [ -z "$metadata_version" ]; then
  echo "ERROR: Failed to read a version from a release file."
  exit 1
fi

if [ "$web_version" != "$conf_version" ] || [ "$web_version" != "$metadata_version" ]; then
  echo "ERROR: Version mismatch detected:"
  echo "  web/src/Qgis2threejs.ts: $web_version"
  echo "  conf.py: $conf_version"
  echo "  metadata.txt: $metadata_version"
  exit 1
fi

expected_version_int=$(printf '%s' "$conf_version" | awk -F. '{ printf "%d%02d%02d", $1, $2, $3 }')
if [ "$conf_version_int" != "$expected_version_int" ]; then
  echo "ERROR: conf.py PLUGIN_VERSION_INT is $conf_version_int; expected $expected_version_int."
  exit 1
fi

echo "Version $web_version is consistent across release files."

printf "Continue? [y/N] "
read ret
[ ${ret} = "y" ] || exit

echo
echo "== Creating release branch =="
git branch -D release.sh > /dev/null 2>&1
git checkout -b release.sh

echo
echo "== Building JavaScript files =="

npm run build:min

if [ $? -ne 0 ]; then
  echo "ERROR: 'npm run build:min' failed."
  exit 1
fi

for file in $JS_FILES
do
    if [ ! -f "$file" ]; then
        echo "Error: Required file not found: $file" >&2
        exit 1
    fi
done

git add -f $JS_FILES
git commit -m "build JavaScript files"

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to commit the build output."
  exit 1
fi

echo
echo "== Switching to release mode =="
sed -i 's/DEBUG_MODE = ./DEBUG_MODE = 0/g' conf.py
git add conf.py
git commit -m "switch to release mode"

# echo "== Translation release =="
# lrelease i18n/*.ts
# git add --all > /dev/null 2>&1
# git commit -m "translation release"

echo
echo "== Removing development files =="
git rm -q .gitignore
git rm -q CONTRIBUTING.md
git rm -q package.json
git rm -q tsconfig.json
git rm -q gui/ui/*.ui
git rm -q -r .github
git rm -q -r docs
git rm -q -r scripts
git rm -q -r web/src
git rm -q -r tests
git commit -q -m "remove development files"

echo
echo "== Git status =="
git status

echo
echo "== Create release archive =="
printf "Ok? [y/N] "
read ret
[ ${ret} = "y" ] || exit

echo Creating archive...
git archive --prefix=${PLUGINNAME}/ -o ${PLUGINNAME}.zip release.sh

echo
echo "============================================================"
echo " Release process completed"
echo "============================================================"
ls -lh "${PLUGINNAME}.zip"
