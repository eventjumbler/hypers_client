import asyncio
import logging
import sys
from abc import ABC, abstractmethod

import requests

_LOG = logging.getLogger(__name__)


def factory(mode, loop=None, endpoint='', access_key='', secret_key='', region=''):
    _LOG.info('Mode: %s | Endpoint: %s', mode, endpoint)
    from .docker_client import DockerClient
    from .hypersh import HypershClient
    if mode == DockerClient.identifier():
        return DockerClient(loop=loop, endpoint=endpoint)
    if mode == HypershClient.identifier():
        return HypershClient(loop=loop, endpoint=endpoint, access_key=access_key, secret_key=secret_key, region=region)
    raise TypeError('Not found docker client for provider %s' % mode)


def _init_loop():
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    return loop


class IDockerProvider(ABC):

    def __init__(self, loop, endpoint):
        if loop:
            self.loop = loop
        else:
            self.loop = _init_loop()
        self.endpoint = endpoint
        self.session = requests.Session()
        super().__init__()

    @abstractmethod
    def _init_header(self):
        headers = {}
        headers['content-type'] = 'application/json'
        return headers

    @abstractmethod
    def _get_auth(self):
        pass

    def pull_image(self, image, tag='latest', fail_if_exist=False):
        _LOG.info('Pull image %s, tag %s', image, tag)
        is_available = self.check_image_available(image, tag)
        if not is_available:
            if fail_if_exist:
                _LOG.error('Image: %s:%s already existed', image, tag)
                return False
            return True
        # TODO: Missing X-Registry-Auth – base64-encoded AuthConfig object, containing either login information, or a toke
        create_image_resp = self.session.post(
            self.endpoint + '/images/create?fromImage=%s&tag=%s' % (image, tag),
            auth=self._get_auth(), headers=self._init_header()
        )
        self._debug(create_image_resp)
        if create_image_resp.status_code not in (200, 201):
            _LOG.error('Pull image failed, status: %s  -  %s', create_image_resp.status_code, create_image_resp.content.decode())
            return False
        return True

    # TODO: Should separate between docker and hyper. Hyper seems not support filter by tag
    def check_image_available(self, image, tag='latest'):
        repo_tag = '%s:%s' % (image, tag)
        _LOG.info('List images then filter image %s', repo_tag)
        images_list_resp = self.session.get(
            self.endpoint + '/images/json',
            auth=self._get_auth(), headers=self._init_header()
        )
        self._debug(images_list_resp)
        if images_list_resp.status_code not in (200, 201):
            _LOG.error('GET /containers/ failed, status: %s  -  %s', images_list_resp.status_code, images_list_resp.content.decode())
            return False, None
        images = [di for di in images_list_resp.json() if repo_tag in di['RepoTags']]
        return not images

    def get_containers(self, state=None, image=None):
        _LOG.info('List containers by state %s, image %s', state, image)
        containers_list_resp = self.session.get(
            self.endpoint + '/containers/json?all=1',
            auth=self._get_auth(), headers=self._init_header()
        )
        self._debug(containers_list_resp)
        if containers_list_resp.status_code not in (200, 201):
            _LOG.error('GET /containers/ failed, status: %s  -  %s', containers_list_resp.status_code, containers_list_resp.content.decode())
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
        _LOG.info('Remove Container from image: %s', image)
        success, containers = self.get_containers(image == image)
        if not success:
            return False
        for di in containers:
            if not self.remove_container(di['id']):
                _LOG.warning('Failed to remove container ' + di['id'])
        return True

    def remove_container(self, container_id):
        _LOG.info('Remove Container: %s', container_id)
        delete_resp = self.session.delete(
            self.endpoint + ('/containers/%s' % container_id) + '?v=1&force=1',
            auth=self._get_auth(), headers=self._init_header()
        )
        self._debug(delete_resp)
        if delete_resp.status_code not in (200, 201):
            return False
        return True

    def create_container(self, image, name=None, size='M2', env_vars=None, cmd=None, tcp_ports=None, links=[]):
        _LOG.info('Create Container: Image %s - Name %s', image, name)
        env_vars = env_vars or {}
        tcp_ports = tcp_ports or []
        query_str = '?name=' + name if name else ''
        post_dict = {'Image': image, 'Labels': {'sh_hyper_instancetype': size}}
        if name:
            post_dict['Hostname'] = name
        if env_vars:
            post_dict['Env'] = ['%s=%s' % (k, v) for (k, v) in env_vars.items()]
        if cmd:
            post_dict['Cmd'] = cmd
        post_dict['HostConfig'] = {'NetworkMode': 'bridge'}
        if tcp_ports:
            post_dict['HostConfig']['PortBindings'] = {"%s/tcp" % p: [{"HostPort": str(p)}] for p in tcp_ports}
        if links:
            post_dict['HostConfig']['Links'] = links
        auth = self._get_auth()
        headers = self._init_header()
        create_container_resp = self.session.post(
            self.endpoint + '/containers/create' + query_str,
            json=post_dict,
            auth=auth, headers=headers
        )
        self._debug(create_container_resp)
        if create_container_resp.status_code not in (200, 201, 204, 304):
            _LOG.error('/containers/create failed, status: %s  -  %s', create_container_resp.status_code, create_container_resp.content.decode())
            return False, None
        create_container_resp = create_container_resp.json()
        container_id = create_container_resp['Id']
        success = self.start_container(container_id)
        return success, container_id

    def start_container(self, container_id):  # not sure if this is necessary?
        _LOG.info('Start Container: %s', container_id)
        start_container_resp = self.session.post(
            self.endpoint + '/containers/%s/start' % container_id,
            auth=self._get_auth(), headers=self._init_header()
        )
        self._debug(start_container_resp)
        # 204 = no error, 304 = container already started
        if start_container_resp.status_code not in (200, 201, 204, 304):
            _LOG.error('/containers/%s/start failed: %s', container_id, start_container_resp.content.decode())
        return start_container_resp.status_code in (200, 201, 204, 304)

    def inspect_container(self, container_id):
        _LOG.info('Inspect Container: %s', container_id)
        inspect_response = self.session.get(
            self.endpoint + '/containers/%s/json' % container_id,
            auth=self._get_auth(), headers=self._init_header()
        )
        self._debug(inspect_response)
        if inspect_response.status_code not in (200, 201):
            return False, None
        return True, inspect_response.json()

    def _debug(self, response):
        _LOG.debug(response.status_code)
        _LOG.debug(response.text)
