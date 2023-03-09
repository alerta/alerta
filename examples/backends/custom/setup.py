from setuptools import setup

version = '0.0.1'

setup(
    name='alerta-custom-backend',
    version=version,
    description='Alerta custom backend example',
    url='https://github.com/alerta/alerta',
    license='Apache License 2.0',
    author='Victor Garcia',
    author_email='victor.garcia@datadope.io',
    packages=['package'],
    install_requires=[],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'alerta.database.backends': [
            'custom = package'
        ]
    }
)
