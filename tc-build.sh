#!/bin/bash

if [ -z "$BUILD_NUMBER" ]
then
	echo "ERROR: BUILD_NUMBER environment variable not set by TeamCity"
	exit 1
fi

VERSION=$(<VERSION)

SCRIPT=$(readlink -f $0)
ALERTA_VCS_ROOT=`dirname $SCRIPT`

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
pushd contrib/riffraff/
zip ${ALERTA_VCS_ROOT}/artifacts.zip deploy.json
popd
pushd ${BUILDROOT}/RPMS/x86_64/
zip -r ${ALERTA_VCS_ROOT}/artifacts.zip alerta-${VERSION}-${BUILD_NUMBER}.x86_64.rpm alerta-extras-${VERSION}-${BUILD_NUMBER}.x86_64.rpm zip
popd

# Pushlish artifact
echo "##teamcity[publishArtifacts '${ALERTA_VCS_ROOT}/artifacts.zip => .']"

