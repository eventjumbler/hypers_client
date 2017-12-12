import unittest
from dockerrest.docker_provider import factory, IDockerProvider
from dockerrest.docker_client import DockerClient
from dockerrest.hypersh import HypershClient


class CreateContainerTest(unittest.TestCase):

    def test_hyper_client(self):
        provider = factory('hypersh', region='us-west-1')
        self.assertTrue(isinstance(provider, HypershClient))
        self.assertTrue(isinstance(provider, IDockerProvider))
        self.assertFalse(isinstance(provider, DockerClient))
        env = {'SE_OPTS': '-id firefox-ba1c22ddd1', 'NODE_APPLICATION_NAME': 'firefox-ba1c22ddd1'}
        success, container_id = provider.create_container('selenium/node-firefox', name='firefox-ba1c22ddd1',
                                                          size='M2', env_vars=env, links=['c7a144c9db08:hub'])
        print(container_id)
        self.assertTrue(success)

if __name__ == '__main__':
    unittest.main()
