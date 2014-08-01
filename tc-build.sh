#!/bin/bash

# set -x

if [ -z "$BUILD_NUMBER" ]
then
	echo "ERROR: BUILD_NUMBER environment variable not set by TeamCity"
	exit 1
fi

VERSION=$(python -c 'import alerta; print alerta.__version__')
ALERTA_VCS_ROOT=`pwd`

now=`date -u +%Y-%m-%dT%H:%M:%SZ`

cat << EOF > ${ALERTA_VCS_ROOT}/alerta/build.py
BUILD_NUMBER = '${BUILD_NUMBER}'
BUILD_DATE = '${now}'
BUILD_VCS_NUMBER = '${BUILD_VCS_NUMBER}'
BUILT_BY = '${USER}'
HOSTNAME = '${HOSTNAME}'
EOF

# Clean up previous runs
rm -f ${ALERTA_VCS_ROOT}/artifacts.zip

# Create RPMs build directory tree
BUILDROOT=${ALERTA_VCS_ROOT}/rpmbuild
rm -rf ${BUILDROOT}
mkdir ${BUILDROOT} \
	${BUILDROOT}/SOURCES \
	${BUILDROOT}/SRPMS \
	${BUILDROOT}/SPECS \
	${BUILDROOT}/BUILD \
	${BUILDROOT}/WORKING \
	${BUILDROOT}/RPMS

# Create source tarball
tar zcvf ${BUILDROOT}/SOURCES/alerta-${VERSION}.tar.gz --xform 's,^,alerta-'"${VERSION}"'/,S' --exclude rpmbuild * >/dev/null

# Build RPMs
rpmbuild -v --with teamcity --define "version ${VERSION}" --define "release ${BUILD_NUMBER}" --define "_topdir ${BUILDROOT}" \
	-bb ${ALERTA_VCS_ROOT}/contrib/redhat/alerta-server.spec || exit 1

# Check RPMs
rpm -Kv ${BUILDROOT}/RPMS/x86_64/alerta-server-${VERSION}-${BUILD_NUMBER}.x86_64.rpm
rpm -Kv ${BUILDROOT}/RPMS/x86_64/alerta-extras-${VERSION}-${BUILD_NUMBER}.x86_64.rpm

# Create archive
pushd ${BUILDROOT}
cp ${ALERTA_VCS_ROOT}/contrib/riffraff/deploy.json .
mkdir -p packages/alerta-server
mv ${BUILDROOT}/RPMS/x86_64/alerta-server-${VERSION}-${BUILD_NUMBER}.x86_64.rpm packages/alerta-server
mkdir -p packages/alerta-extras
mv ${BUILDROOT}/RPMS/x86_64/alerta-extras-${VERSION}-${BUILD_NUMBER}.x86_64.rpm packages/alerta-extras
zip -r ../artifacts.zip deploy.json packages
popd

# Publish artifact
echo "##teamcity[publishArtifacts '${ALERTA_VCS_ROOT}/artifacts.zip => .']"

