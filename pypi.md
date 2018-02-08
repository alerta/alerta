Create new release (use a python3 virt env)

1. Ensure master is up-to-date

    $ get checkout master
    $ git pull

2. Bump version number

    $ vi VERSION
    $ vi alerta/version.py
    $ git add .
    $ git commit -m 'Bump version to 5.x.x'
    $ git push

3. Update git tags

    $ make tags

4. Push wheel to PyPi

    $ make clean
    $ make upload

See http://pythonwheels.com/

