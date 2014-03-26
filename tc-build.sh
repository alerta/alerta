#!/bin/bash

set -e
#set -x

# prep
pushd `dirname $0` >/dev/null
SCRIPT_PATH=`pwd`
popd >/dev/null

rm -Rf $SCRIPT_PATH/app
rm -Rf $SCRIPT_PATH/dashboard
rm -Rf $SCRIPT_PATH/daemons
rm -Rf $SCRIPT_PATH/dist
rm -Rf $SCRIPT_PATH/alerta.egg-info

if [ -z "${BUILD_NUMBER}" ]; then
    BUILD_NUMBER=DEV
fi

pushd $SCRIPT_PATH

echo "#Creating App virtualenv..."
virtualenv app
app/bin/python setup.py clean

echo "#Installing dependencies"
app/bin/pip install -r requirements.txt --upgrade
virtualenv --relocatable app

echo "#Set build number in manifest..."
cat << EOF > alerta/build.py
BUILD_NUMBER = '${BUILD_NUMBER}'
EOF

echo "#Build distribution zip..."
app/bin/python setup.py sdist --formats=zip

mkdir -p dist/packages/app
unzip $SCRIPT_PATH/dist/alerta*.zip -d $SCRIPT_PATH/dist/packages/app

BUILD_DIR=`ls -1 dist/packages/app`
cp -r app dist/packages/app/${BUILD_DIR}


echo "#Creating Dashboard virtualenv..."
virtualenv dashboard
dashboard/bin/python setup.py clean

echo "#Installing dependencies..."
dashboard/bin/pip install -r requirements.txt --upgrade
virtualenv --relocatable dashboard

echo "Build distribution zip"
dashboard/bin/python setup.py sdist --formats=zip

mkdir -p dist/packages/dashboard
unzip $SCRIPT_PATH/dist/alerta*.zip -d $SCRIPT_PATH/dist/packages/app

BUILD_DIR=`ls -1 dist/packages/dashboard`
cp -r dashboard dist/packages/dashboard/${BUILD_DIR}


echo "#Creating Daemon virtualenv..."
virtualenv daemon
daemon/bin/python setup.py clean

echo "#Installing dependencies..."
daemon/bin/pip install -r requirements.txt --upgrade
virtualenv --relocatable daemon

echo "Build distribution zip"
daemon/bin/python setup.py sdist --formats=zip

mkdir -p dist/packages/daemon
unzip $SCRIPT_PATH/dist/alerta*.zip -d $SCRIPT_PATH/dist/packages/daemon

BUILD_DIR=`ls -1 dist/packages/daemon`
cp -r daemon dist/packages/daemon/${BUILD_DIR}


echo "#Create artifact.zip..."
cp contrib/riffraff/deploy.json dist/
pushd dist
zip -r artifacts.zip deploy.json packages
popd
echo "#Rezipped to artifacts.zip"
popd

echo "#Create console scripts"
app/bin/python setup.py install

echo "##teamcity[publishArtifacts '$SCRIPT_PATH/dist/artifacts.zip => .']"
