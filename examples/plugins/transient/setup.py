from setuptools import find_packages, setup

version = '0.0.1'

setup(
    name='alerta-transient',
    version=version,
    description='Example Alerta plugin for transient flapping alerts',
    url='https://github.com/alerta/alerta-contrib',
    license='Apache License 2.0',
    author='Your name',
    author_email='your.name@example.com',
    packages=find_packages(),
    py_modules=['alerta_transient'],
    install_requires=[],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'alerta.plugins': [
            'transient = alerta_transient:TransientAlert'
        ]
    }
)
