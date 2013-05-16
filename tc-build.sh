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
SCRIPT=$(readlink -f $0)
ALERTA_VCS_ROOT=`dirname $SCRIPT`

# create a build root for the rpms
BUILDROOT=${ALERTA_VCS_ROOT}/rpmtarget
rm -rf ${BUILDROOT}
mkdir ${BUILDROOT} \
	${BUILDROOT}/SOURCES \
	${BUILDROOT}/SRPMS \
	${BUILDROOT}/SPECS \
	${BUILDROOT}/BUILD \
	${BUILDROOT}/BUILD/alerta-${BUILD_NUMBER} \
	${BUILDROOT}/RPMS

# copy files for the RPM build into the build root sources
rsync -av --exclude='.git/' --exclude-from=$ALERTA_VCS_ROOT/.gitignore ${ALERTA_VCS_ROOT}/ ${BUILDROOT}/BUILD/ || exit 1

# now run the rpm build with a spec file
rpmbuild --define "version ${VERSION}" --define "_topdir ${BUILDROOT}" -bb ${ALERTA_VCS_ROOT}/alerta.spec || exit 1

# now we have a bunch of RPM files which we should flag as artifacts
echo "##teamcity[publishArtifacts '${BUILDROOT}/RPMS/noarch/alerta-*-${VERSION}-1-noarch.rpm => .']"
