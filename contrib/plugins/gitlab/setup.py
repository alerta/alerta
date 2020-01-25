from setuptools import find_packages, setup

version = '6.1.0'

setup(
    name='alerta-gitlab',
    version=version,
    description='Example Alerta plugin for GitLab Issues',
    url='https://github.com/alerta/alerta',
    license='MIT',
    author='Nick Satterly',
    author_email='nick.satterly@gmail.com',
    packages=find_packages(),
    py_modules=['alerta_gitlab'],
    install_requires=[
        'requests'
    ],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'alerta.plugins': [
            'gitlab = alerta_gitlab:GitlabIssue'
        ]
    }
)
