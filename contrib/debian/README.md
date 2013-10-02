To build alerta debian packages for client, server and common:

    $ git clone https://github.com/guardian/alerta.git alerta
    $ cd alerta
    $ python setup.py --command-packages=stdeb.command sdist_dsc
    $ cd deb_dist/alerta-x.y.z/
    $ cp ../../contrib/debian/* debian/
    $ dpkg-buildpackage -rfakeroot -uc -us
    $ cd ..
    $ sudo dpkg -i *.deb
