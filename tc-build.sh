#!/bin/bash
# Build script for teamcity to build the alerta RPMs

if [ -z "$BUILD_NUMBER" ]
then
	echo "ERROR: BUILD_NUMBER environment variable not set by TeamCity"
	exit 1
fi

VERSION="3.0.0"

SCRIPT=$(readlink -f $0)
ALERTA_VCS_ROOT=`dirname $SCRIPT`

BUILDROOT=${ALERTA_VCS_ROOT}/rpmtarget
rm -rf ${BUILDROOT}
mkdir ${BUILDROOT} \
	${BUILDROOT}/SOURCES \
	${BUILDROOT}/SRPMS \
	${BUILDROOT}/SPECS \
	${BUILDROOT}/BUILD \
	${BUILDROOT}/WORKING \
	${BUILDROOT}/RPMS

git archive --format=tar --prefix="alerta-${version}/" HEAD | gzip > ${BUILDROOT}/SOURCES/alerta-${version}.tar.gz

rpmbuild --define "version ${VERSION}" --define "release ${BUILD_NUMBER}" --define "_topdir ${BUILDROOT}" -bb ${ALERTA_VCS_ROOT}/alerta.spec || exit 1

echo "##teamcity[publishArtifacts '${BUILDROOT}/RPMS/noarch/alerta-${VERSION}-${BUILD_NUMBER}.noarch.rpm => .']"
echo "##teamcity[publishArtifacts '${BUILDROOT}/RPMS/noarch/alerta-extras-${VERSION}-${BUILD_NUMBER}.noarch.rpm => .']"
