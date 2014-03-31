#!/bin/bash

if [ -z "$BUILD_NUMBER" ]
then
	echo "ERROR: BUILD_NUMBER environment variable not set by TeamCity"
	exit 1
fi

VERSION=$(<VERSION)
ALERTA_VCS_ROOT=`pwd`

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
tar zcvf ${BUILDROOT}/SOURCES/alerta-${VERSION}.tar.gz --xform 's,^,alerta-'"${VERSION}"'/,S' * >/dev/null

# Build RPMs
rpmbuild -v --with teamcity --define "version ${VERSION}" --define "release ${BUILD_NUMBER}" --define "_topdir ${BUILDROOT}" -bb ${ALERTA_VCS_ROOT}/alerta.spec || exit 1

# Create archive
pushd ${BUILDROOT}
cp ${ALERTA_VCS_ROOT}/contrib/riffraff/deploy.json .
mkdir -p packages/alerta
mv ${BUILDROOT}/RPMS/x86_64/alerta-${VERSION}-${BUILD_NUMBER}.x86_64.rpm packages/alerta
mkdir -p packages/alerta-extras
mv ${BUILDROOT}/RPMS/x86_64/alerta-extras-${VERSION}-${BUILD_NUMBER}.x86_64.rpm packages/alerta-extras
zip ../artifacts.zip deploy.json packages
popd

# Publish artifact
echo "##teamcity[publishArtifacts '${ALERTA_VCS_ROOT}/artifacts.zip => .']"

