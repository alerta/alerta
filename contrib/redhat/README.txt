$ git clone https://github.com/guardian/alerta.git alerta-2.0.0
$ tar zcvf alerta.tar.gz --exclude=.git alerta-2.0.0/*
$ cp alerta.tar.gz ~/rpmbuild/SOURCES/alerta-2.0.0.tar.gz
$ cd ~/rpmbuild/SPECS
$ rpmbuild -bb alerta.spec