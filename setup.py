import os
from setuptools import setup

# to install run: python setup.py install

INSTALL_REQUIREMENTS = [
    'requests',
]

setup(
    name = "hypersh-client",
    version = "0.0.10",
    author = "Ross Rochford",
    packages=['hypersh_client'],
    install_requires=INSTALL_REQUIREMENTS,    
    classifiers=[],
)
