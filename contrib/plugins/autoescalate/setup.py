from setuptools import find_packages, setup

version = '0.0.1'

setup(
    name='autoescalate',
    version=version,
    description='Alerta plugin to escalate severity based on duplicate count',
    url='',
    license='MIT',
    author='Nicki de Wet',
    author_email='ndewet@ecentric.co.za',
    packages=find_packages(),
    py_modules=['autoescalate'],
    install_requires=[],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'alerta.plugins': [
            'autoescalate = autoescalate:AutoEscalateSeverity'
        ]
    }
)
