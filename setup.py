import os
from setuptools import setup

# to install run: python setup.py install

INSTALL_REQUIREMENTS = [
    'requests',
]

setup(
    name = "hypersh-client",
    version = "0.0.12",
    author = "Ross Rochford",
    packages=['hypersh_client'],
    install_requires=INSTALL_REQUIREMENTS,    
    classifiers=[],
)
