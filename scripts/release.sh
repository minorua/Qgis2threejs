# A script to release the plugin
#       begin: 2013-12-02
# last update: 2015-10-01

# add OSGeo4W/bin to PATH
export PATH=$PATH:/c/OSGeo4W/bin

p=`pwd`
PLUGINNAME=`basename ${p}`
echo ${PLUGINNAME} release process started

# clean up
rm -r *.pyc
rm -f ${PLUGINNAME}.zip

# version check
echo [Check] js/Qgis2threejs.js version updated?
echo [Check] plugin_version in settings.py updated?
echo [Check] metadata.txt version updated?
echo -n [Check] docs/conf.py version updated? [y/n]...
read ret
if [ ${ret} != "y" ]; then exit; fi

# move to release.sh branch
git branch -D release.sh > /dev/null 2>&1
git checkout -b release.sh

echo [Task] set debug_mode=0
sed -i 's/debug_mode = 1/debug_mode = 0/g' *.py

# echo [Task] translation release
# lrelease i18n/*.ts

git add --all > /dev/null 2>&1
git commit -m "switch to release mode and translation release" > /dev/null 2>&1

# remove dev files from git index
git rm .gitignore
git rm -r docs
git rm -r scripts
git rm -r tests
git rm ui/*.ui
git commit -m "remove development files"

git status
#> ../release_log.diff 2>&1

echo -n [Check] are you ready to archive? [y/n]...
read ret
if [ ${ret} != "y" ]; then exit; fi

# archive release.sh branch
echo archiving ${PLUGINNAME}...
git archive --prefix=${PLUGINNAME}/ -o ${PLUGINNAME}.zip release.sh

echo Release process finished
ls *.zip
