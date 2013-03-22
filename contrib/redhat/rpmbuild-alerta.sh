#!/bin/sh

VERSION=2.0.0

cd ~/git
rm -fR ~/git/alerta-${VERSION}
git clone https://github.com/guardian/alerta.git alerta-${VERSION}
sleep 5
tar zcvf alerta.tar.gz --exclude=.git alerta-${VERSION}/*
cp alerta.tar.gz ~/rpmbuild/SOURCES/alerta-${VERSION}.tar.gz
cd ~/rpmbuild/SPECS
rpmbuild -bb alerta.spec
