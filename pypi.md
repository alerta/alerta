Create new release (use a python3 virt env)

1. Ensure master is up-to-date
```bash
    $ git checkout master
    $ git pull
```
2. Bump version number
```bash
    $ vi VERSION
    $ vi alerta/version.py
    $ git add .
    $ git commit -m 'Bump version to 5.x.x'
    $ git push
```
3. Update git tags
```bash
    $ make tag
```
4. Push wheel to PyPi
```bash
    $ make clean
    $ make upload
```
See http://pythonwheels.com/

