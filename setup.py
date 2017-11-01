import pip
from setuptools import setup, find_packages

_LINKS = []  # for repo urls (dependency_links)
_REQUIRES = []  # for package names

requirements = pip.req.parse_requirements(
    'requirements.txt', session=pip.download.PipSession()
)

for item in requirements:
    print(item)
    if getattr(item, 'url', None):
        _LINKS.append(str(item.url))
    if getattr(item, 'link', None):
        _LINKS.append(str(item.link))
    if item.req:
        _REQUIRES.append(str(item.req))

setup(
    name="hypersh-client",
    version="0.0.13",
    author="Ross Rochford",
    license="MIT",
    description="Hypersh python client",
    packages=find_packages(exclude=['tests']),
    install_requires=_REQUIRES,
    dependency_links=_LINKS
)
