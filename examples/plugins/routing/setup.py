from setuptools import find_packages, setup

version = '0.0.1'

setup(
    name='alerta-routing',
    version=version,
    description='Alerta routing rules for blackout notifications',
    url='https://github.com/alerta/alerta-contrib',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@theguardian.com',
    packages=find_packages(),
    py_modules=['routing'],
    install_requires=[],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'alerta.routing': [
            'rules = routing:rules'
        ]
    }
)
