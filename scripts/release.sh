# Release script for plugin
#   begin: 2013-12-02

export PATH=$PATH:/c/OSGeo4W/bin

PLUGINNAME=Qgis2threejs

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
rm -f web/js/Qgis2threejs.js
rm -f web/js/Qgis2threejs.js.map

echo
echo "== Version check =="
echo "Please confirm:"
echo "  - web/js/src/index.js version is updated"
echo "  - PLUGIN_VERSION and PLUGIN_VERSION_INT in conf.py are updated"
echo "  - metadata.txt version is updated"

printf "Continue? [y/N] "
read ret
[ ${ret} = "y" ] || exit

echo
echo "== Creating release branch =="
git branch -D release.sh > /dev/null 2>&1
git checkout -b release.sh

echo
echo "== Building Qgis2threejs.js =="

npm run build:min

if [ $? -ne 0 ]; then
  echo "ERROR: Qgis2threejs.js build failed."
  exit 1
fi

git add -f web/js/Qgis2threejs.js
git commit -m "build Qgis2threejs.js"

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to commit Qgis2threejs.js."
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
git rm -q -r tests
git rm -q -r web/js/src
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
