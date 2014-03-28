#!/bin/bash

set -x

if [ -z "$BUILD_NUMBER" ]
then
	echo "ERROR: BUILD_NUMBER environment variable not set by TeamCity"
	exit 1
fi

VERSION="3.0.0"

SCRIPT=$(readlink -f $0)
ALERTA_VCS_ROOT=`dirname $SCRIPT`

BUILDROOT=${ALERTA_VCS_ROOT}/rpmbuild
rm -rf ${BUILDROOT}
mkdir ${BUILDROOT} \
	${BUILDROOT}/SOURCES \
	${BUILDROOT}/SRPMS \
	${BUILDROOT}/SPECS \
	${BUILDROOT}/BUILD \
	${BUILDROOT}/WORKING \
	${BUILDROOT}/RPMS

tar zcvf ${BUILDROOT}/SOURCES/alerta-${VERSION}.tar.gz --xform 's,^,alerta-3.0.0/,S' * >/dev/null

rpmbuild --define "version ${VERSION}" --define "release ${BUILD_NUMBER}" --define "_topdir ${BUILDROOT}" -bb ${ALERTA_VCS_ROOT}/alerta.spec || exit 1

echo "##teamcity[publishArtifacts '${BUILDROOT}/RPMS/noarch/alerta-${VERSION}-${BUILD_NUMBER}.noarch.rpm => .']"
echo "##teamcity[publishArtifacts '${BUILDROOT}/RPMS/noarch/alerta-extras-${VERSION}-${BUILD_NUMBER}.noarch.rpm => .']"
