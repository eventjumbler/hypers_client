import re
import pip
from setuptools import setup, find_packages


_LINKS = []  # for repo urls (dependency_links)
_REQUIRES = []  # for package names


def __normalize(req):
    # Strip off -dev, -0.2, etc.
    match = re.search(r'^(.*?)(?:-dev|-\d.*)$', req)
    return match.group(1) if match else req

requirements = pip.req.parse_requirements(
    'requirements.txt', session=pip.download.PipSession()
)

for item in requirements:
    has_link = False
    if getattr(item, 'url', None):
        _LINKS.append(str(item.url))
        has_link = True
    if getattr(item, 'link', None):
        _LINKS.append(str(item.link))
        has_link = True
    if item.req:
        req = str(item.req)
        _REQUIRES.append(__normalize(req) if has_link else req)

setup(
    name="hypersh-client",
    version="0.1.0",
    author="Ross Rochford",
    license="MIT",
    description="Hypersh python client",
    packages=find_packages(exclude=['tests']),
    install_requires=_REQUIRES,
    dependency_links=_LINKS
)
