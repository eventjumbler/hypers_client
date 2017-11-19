#!/usr/bin/python

import logging
import requests
import datetime
import time
import os
from uuid import uuid4

from ..aws4auth2.aws4auth_hypersh import AWS4Auth

_ENDPOINTS = {
    'us-west-1': "https://us-west-1.hyper.sh/v1.23",
    'eu-central-1': "https://eu-central-1.hyper.sh/v1.23",
}
_LOG = logging.getLogger(__name__)


class HypershClient(object):

    def __init__(self, access_key=os.environ['HYPERSH_ACCESS_KEY'], secret_key=os.environ['HYPERSH_SECRET'], region=os.environ['HYPERSH_REGION']):
        self.hyper_endpoint = _ENDPOINTS[region]
        if not self.hyper_endpoint:
            raise Exception('invalid region: %s' % region)
        self.hyper_auth = AWS4Auth(access_key, secret_key, region, "hyper")
        self.session = requests.Session()

    @classmethod
    def _get_headers(cls):
        now = datetime.datetime.utcnow()
        headers = {}
        headers['x-hyper-date'] = now.strftime('%Y%m%dT%H%M%SZ')
        headers['content-type'] = 'application/json'
        return headers

    def get_containers(self, state=None, image=None):
        containers_list_resp = self.session.get(
            self.hyper_endpoint + '/containers/json?all=1',
            auth=self.hyper_auth, headers=self._get_headers()
        )
        _LOG.debug(containers_list_resp)
        if containers_list_resp.status_code not in (200, 201):
            _LOG.error('GET /containers/ failed, status: %s  -  %s' % (containers_list_resp.status_code, containers_list_resp.content.decode()))
            return False, None
        containers = [di for di in containers_list_resp.json()]
        if state:
            containers = [di for di in containers if di['State'] == state]
        if image:
            containers = [di for di in containers if di['Image'] == image]
        containers = [
            {'id': di['Id'], 'name': di['Names'][0].lstrip('/'), 'state': di['State'], 'image': di['Image']}
            for di in containers
        ]
        return True, containers

    def remove_all_containers_with_image(self, image):
        success, containers = self.get_containers(image == image)
        if not success:
            return False
        for di in containers:
            if not self.remove_container(di['id']):
                _LOG.warning('Failed to remove container ' + di['id'])
        return True

    def remove_container(self, container_id):
        delete_resp = self.session.delete(
            self.hyper_endpoint + ('/containers/%s' % container_id) + '?v=1&force=1',
            auth=self.hyper_auth, headers=self._get_headers()
        )
        _LOG.debug(delete_resp)
        if delete_resp.status_code not in (200, 201):
            return False
        return True

    def create_container(self, image, name=None, size='M2', environment_variables=None, cmd=None, tcp_ports=None, links=[]):
        environment_variables = environment_variables or {}
        tcp_ports = tcp_ports or []
        query_str = '?name=' + name if name else ''
        post_dict = {'Image': image, 'Labels': {'sh_hyper_instancetype': size}}
        if name:
            post_dict['Hostname'] = name
        if environment_variables:
            post_dict['Env'] = [k + '=' + v.decode().strip() for (k, v) in environment_variables.items()]
        if cmd:
            post_dict['Cmd'] = cmd
        post_dict['HostConfig'] = {}
        if tcp_ports:
            post_dict['HostConfig']['PortBindings'] = {"%s/tcp" % p: [{"HostPort": str(p)}] for p in tcp_ports}
        if links:
            post_dict['HostConfig']['Links'] = links
        auth = self.hyper_auth
        headers = self._get_headers()
        create_container_resp = self.session.post(
            self.hyper_endpoint + '/containers/create' + query_str,
            json=post_dict,
            auth=auth, headers=headers
        )
        _LOG.debug(create_container_resp)
        if create_container_resp.status_code not in (200, 201, 204, 304):
            _LOG.error('/containers/create failed, status: %s  -  %s', create_container_resp.status_code, create_container_resp.content.decode())
            return False, None
        create_container_resp = create_container_resp.json()
        container_id = create_container_resp['Id']
        success = self.start_container(container_id)
        return success, container_id

    def start_container(self, container_id):  # not sure if this is necessary?
        start_container_resp = self.session.post(
            self.hyper_endpoint + '/containers/%s/start' % container_id,
            auth=self.hyper_auth, headers=self._get_headers()
        )
        _LOG.debug(start_container_resp)
        # 204 = no error, 304 = container already started
        if start_container_resp.status_code not in (200, 201, 204, 304):
            _LOG.error('/containers/%s/start failed: %s' % (container_id, start_container_resp.content.decode()))
        return start_container_resp.status_code in (200, 201, 204, 304)

    def get_fips(self):
        fips_resp = self.session.get(
            self.hyper_endpoint + '/fips', auth=self.hyper_auth,
            headers=self._get_headers()
        )
        _LOG.debug(fips_resp.text)
        if fips_resp.status_code not in (200, 201):
            return False, None
        fips = [di['fip'] for di in fips_resp.json()]
        return True, fips

    def attach_fip(self, container_id, fip):
        attach_resp = self.session.post(
            self.hyper_endpoint + '/fips/attach?ip=%(fip)s&container=%(container_id)s' % {
                'fip': fip,
                'container_id': container_id
            },
            auth=self.hyper_auth, headers=self._get_headers()
        )
        _LOG.debug(attach_resp.text)
        if attach_resp.status_code not in (200, 201):
            return False
        return True

    def inspect_container(self, container_id):
        inspect_response = self.session.get(
            self.hyper_endpoint + '/containers/%s/json' % container_id,
            auth=self.hyper_auth, headers=self._get_headers()
        )
        _LOG.debug(inspect_response.text)
        if inspect_response.status_code not in (200, 201):
            return False, None
        return True, inspect_response.json()
