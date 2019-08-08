import logging

import requests

from .docker_provider import IDockerProvider

_LOG = logging.getLogger(__name__)


class DockerClient(IDockerProvider):

    def __init__(self, loop, endpoint):
        if not endpoint.strip():
            raise ValueError('Docker REST Endpoint is mandatory')
        super().__init__(loop, endpoint)

    def _init_header(self):
        return super()._init_header()

    def _get_auth(self):
        return {}

    @staticmethod
    def identifier():
        return 'docker'
