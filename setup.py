"""depup installation script."""

from setuptools import setup

setup(
    name='depup',
    version='0.1',
    packages=['src', ],
    data_files=[('src/templates', ['src/templates/default.trac'])],
    scripts=['depup'],
    install_requires=['jinja2'],
    tests_require=['pytest'],
    setup_requires=['pytest-runner'],
)
