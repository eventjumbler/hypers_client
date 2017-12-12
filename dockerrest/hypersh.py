#!/usr/bin/python

import asyncio
import asyncio.subprocess
import datetime
import logging
import os
import shlex
import sys

from .aws4auth2.aws4auth_hypersh import AWS4Auth
from .docker_client import IDockerProvider

_LOG = logging.getLogger(__name__)


class HypershClient(IDockerProvider):

    _ENDPOINTS = {
        'us-west-1': "https://us-west-1.hyper.sh/v1.23",
        'eu-central-1': "https://eu-central-1.hyper.sh/v1.23",
    }

    def __init__(self, loop=None, endpoint='', access_key='', secret_key='', region=''):
        access_key = access_key.strip() or os.getenv('HYPERSH_ACCESS_KEY')
        secret_key = secret_key.strip() or os.getenv('HYPERSH_SECRET')
        region = region.strip() or os.getenv('HYPERSH_REGION', 'eu-central-1')
        endpoint = endpoint.strip() or self._ENDPOINTS.get(region)
        if not endpoint:
            raise Exception('Invalid region: %s' % region)
        self.hyper_auth = AWS4Auth(access_key, secret_key, region, "hyper")
        super().__init__(loop, endpoint)

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
        _LOG.info('Get List IPs')
        fips_resp = self.session.get(
            self.endpoint + '/fips', auth=self._get_auth(),
            headers=self._init_header()
        )
        self._debug(fips_resp)
        if fips_resp.status_code not in (200, 201):
            return False, None
        fips = [di['fip'] for di in fips_resp.json()]
        return True, fips

    def attach_fip(self, container_id, fip):
        _LOG.info('Attach IP %s to container %s', fip, container_id)
        attach_resp = self.session.post(
            self.endpoint + '/fips/attach?ip=%(fip)s&container=%(container_id)s' % {
                'fip': fip,
                'container_id': container_id
            },
            auth=self._get_auth(), headers=self._init_header()
        )
        self._debug(attach_resp)
        if attach_resp.status_code not in (200, 201):
            return False
        return True

    def create_container(self, image, name=None, size='M2', env_vars=None, cmd=None, tcp_ports=None, links=[]):
        if not links:
            return super().create_container(image, name=name, size=size, env_vars=env_vars, cmd=cmd, tcp_ports=tcp_ports, links=[])
        _LOG.info('Hypersh create Container with links via CLI: Image %s - Name %s', image, name)
        env_vars = env_vars or {}
        tcp_ports = tcp_ports or []
        cli = 'hyper run -d '
        cli += '--name %s ' % name if name else ''
        cli += '--size %s ' % size if size else ''
        cli += ' '.join(['-e %s="%s"' % (k, v) for (k, v) in env_vars.items()]) + ' ' if env_vars else ''
        cli += ' '.join(['-p %s:%s' % port for port in tcp_ports]) + ' ' if tcp_ports else ''
        cli += ' '.join(['--link %s' % link for link in links]) + ' ' if links else ''
        cli += '%s %s' % (image, cmd if cmd else '')
        _LOG.debug('CLI to start container: %s', cli)
        success, out, err = self.loop.run_until_complete(self.sys_call_async(shlex.split(cli)))
        if not success:
            _LOG.error('Create HyperSH Container failed, status: %s  -  %s', success, err)
            return success, err
        return success, out

    async def sys_call_async(self, command):
        proc = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.wait()
        stdout, stderr = await proc.communicate()
        success = proc.returncode == 0
        return success, stdout.decode(), stderr.decode()
