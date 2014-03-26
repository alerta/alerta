#!/bin/bash

set -e
#set -x

# prep
pushd `dirname $0` >/dev/null
SCRIPT_PATH=`pwd`
popd >/dev/null

rm -Rf $SCRIPT_PATH/ve
rm -Rf $SCRIPT_PATH/dist
rm -Rf $SCRIPT_PATH/alerta.egg-info

if [ -z "${BUILD_NUMBER}" ]; then
    BUILD_NUMBER=DEV
fi

pushd $SCRIPT_PATH

echo "creating virtualenv"
virtualenv ve
echo "cleaning"
ve/bin/python setup.py clean

echo "installing dependencies"
ve/bin/pip install -r requirements.txt --upgrade
virtualenv --relocatable ve

echo "overwriting manifest.py"
cat << EOF > alerta/build.py
BUILD_NUMBER = '${BUILD_NUMBER}'
EOF

echo "Build distribution zip"
ve/bin/python setup.py sdist --formats=zip

mkdir -p dist/packages/alerta
unzip $SCRIPT_PATH/dist/alerta*.zip -d $SCRIPT_PATH/dist/packages/alerta

BUILD_DIR=`ls -1 dist/packages/alerta`
cp -r ve dist/packages/alerta/${BUILD_DIR}
cp contrib/riffraff/deploy.json dist/
pushd dist
zip -r artifacts.zip deploy.json packages
popd
echo "Rezipped to artifacts.zip"
popd

echo "Create console scripts"
ve/bin/python setup.py install

echo "##teamcity[publishArtifacts '$SCRIPT_PATH/dist/artifacts.zip => .']"
