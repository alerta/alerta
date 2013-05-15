#!/bin/bash
# Build script for teamcity to build the alerta RPMs

# check for some required environmentals
if [ -z "$BUILD_NUMBER" ]
then
	echo "No BUILD_NUMBER environment varible set - this is usually set by TeamCity"
	exit 1
fi

VERSION="2.0.${BUILD_NUMBER}"

# work out the directory we are in
ALERTA_VCS_ROOT=`dirname $0`

# create a build root for the rpms
BUILDROOT=${ALERTA_VCS_ROOT}/rpmtarget
mkdir ${BUILDROOT} \
	${BUILDROOT}/SOURCES \
	${BUILDROOT}/SRPMS \
	${BUILDROOT}/SPECS \
	${BUILDROOT}/BUILD \
	${BUILDROOT}/BUILD/alerta-${BUILD_NUMBER} \
	${BUILDROOT}/RPMS

# copy files for the RPM build into the build root sources
rsync -az --exclude='rpmtarget/' ${ALERTA_VCS_ROOT}/ ${BUILDROOT}/BUILD/alerta-${BUILD_NUMBER}/

# now run the rpm build with a spec file
rpmbuild --define "version ${VERSION}" --buildroot ${BUILDROOT} -ba ${ALERTA_VCS_ROOT}/alerta.spec

# now we have a bunch of RPM files which we should flag as artifacts
echo "##teamcity[publishArtifacts '${BUILDROOT}/RPMS/noarch/alerta-*-${VERSION}-1-noarch.rpm => .']"