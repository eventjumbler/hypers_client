#!/usr/bin/python

import datetime
import logging
import os

from .aws4auth2.aws4auth_hypersh import AWS4Auth
from .docker_client import IDockerProvider

_LOG = logging.getLogger(__name__)


class HypershClient(IDockerProvider):

    _ENDPOINTS = {
        'us-west-1': "https://us-west-1.hyper.sh/v1.23",
        'eu-central-1': "https://eu-central-1.hyper.sh/v1.23",
    }

    def __init__(self, endpoint='', access_key='', secret_key='', region=''):
        access_key = access_key.strip() or os.getenv('HYPERSH_ACCESS_KEY')
        secret_key = secret_key.strip() or os.getenv('HYPERSH_SECRET')
        region = region.strip() or os.getenv('HYPERSH_REGION', 'eu-central-1')
        endpoint = endpoint.strip() or self._ENDPOINTS.get(region)
        if not endpoint:
            raise Exception('Invalid region: %s' % region)
        self.hyper_auth = AWS4Auth(access_key, secret_key, region, "hyper")
        super().__init__(endpoint)

    def _get_auth(self):
        return self.hyper_auth

    def _init_header(self):
        headers = super()._init_header()
        headers['x-hyper-date'] = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        return headers

    @staticmethod
    def identifier():
        return 'hypersh'

    def get_fips(self):
        fips_resp = self.session.get(
            self.endpoint + '/fips', auth=self._get_auth(),
            headers=self._init_header()
        )
        _LOG.debug(fips_resp.text)
        if fips_resp.status_code not in (200, 201):
            return False, None
        fips = [di['fip'] for di in fips_resp.json()]
        return True, fips

    def attach_fip(self, container_id, fip):
        attach_resp = self.session.post(
            self.endpoint + '/fips/attach?ip=%(fip)s&container=%(container_id)s' % {
                'fip': fip,
                'container_id': container_id
            },
            auth=self._get_auth(), headers=self._init_header()
        )
        _LOG.debug(attach_resp.text)
        if attach_resp.status_code not in (200, 201):
            return False
        return True
