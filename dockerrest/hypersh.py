#!/usr/bin/python
import asyncio
import datetime
import logging
import os
import shlex
# from asyncio.subprocess import PIPE
from subprocess import Popen, PIPE, STDOUT

from .aws4auth2.aws4auth_hypersh import AWS4Auth
from .docker_client import IDockerProvider

_LOG = logging.getLogger(__name__)


class HypershClient(IDockerProvider):

    _ENDPOINTS = {
        'us-west-1': "https://us-west-1.hyper.sh/v1.23",
        'eu-central-1': "https://eu-central-1.hyper.sh/v1.23",
    }

    def __init__(self, loop=None, endpoint='', access_key='', secret_key='', region=''):
        region = region or os.getenv('HYPERSH_REGION', 'eu-central-1')
        endpoint = endpoint or self._ENDPOINTS.get(region)
        if not endpoint:
            raise AttributeError('Invalid region: %s' % region)
        super().__init__(loop, endpoint)
        self.access_key = access_key or os.getenv('HYPERSH_ACCESS_KEY')
        self.secret_key = secret_key or os.getenv('HYPERSH_SECRET')
        self.region = region
        self.hyper_auth = AWS4Auth(self.access_key, self.secret_key, self.region, 'hyper')
        self.__config_hypersh_cli(self.loop)

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
        success, out, err = self.__sys_call(cli)
        if not success:
            _LOG.error('Create HyperSH Container failed, status: %s  -  %s', success, err)
            return success, err
        return success, out

    def __config_hypersh_cli(self, loop):
        cli = 'hyper config --accesskey %s --secretkey %s --default-region %s' % (self.access_key, self.secret_key, self.region)
        success, _, err = self.__sys_call(cli)
        if not success:
            _LOG.warning('HyperSH configuration failed, status: %s  -  %s', success, err)

    def __async_sys_call(self, loop, command):
        async def __call_async(_command):
            proc = await asyncio.create_subprocess_exec(*_command, stdout=PIPE, stderr=PIPE)
            await proc.wait()
            stdout, stderr = await proc.communicate()
            return proc.returncode == 0, stdout.decode(), stderr.decode()
        _LOG.debug(command)
        if loop.is_running():
            _LOG.debug('Loop is running. Init new one')
            return asyncio.new_event_loop().run_until_complete(__call_async(shlex.split(command)))
        return loop.run_until_complete(__call_async(shlex.split(command)))

    def __sys_call(self, command, shell=True):
        _LOG.debug(command)
        proc = Popen(command, stdout=PIPE, stderr=PIPE, shell=shell, universal_newlines=True)
        stdout, stderr = proc.communicate()
        stdout, stderr = stdout if isinstance(stdout, str) else stdout.decode(), stderr if isinstance(stderr, str) else stderr.decode()
        return proc.returncode == 0, stdout.strip(), stderr.strip()
