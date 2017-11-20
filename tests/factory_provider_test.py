import unittest
from dockerrest.docker_provider import factory, IDockerProvider
from dockerrest.docker_client import DockerClient
from dockerrest.hypersh import HypershClient


class TestDockerProvider(unittest.TestCase):

    def test_docker_client(self):
        provider = factory('docker', '172.28.128.3:2375')
        self.assertTrue(isinstance(provider, DockerClient))
        self.assertTrue(isinstance(provider, IDockerProvider))
        self.assertFalse(isinstance(provider, HypershClient))
        self.assertEqual('docker', provider.identifier())
        self.assertEqual({}, provider._get_auth())
        self.assertEqual('172.28.128.3:2375', provider.endpoint)

    def test_hypersh_client(self):
        provider = factory('hypersh')
        self.assertTrue(isinstance(provider, HypershClient))
        self.assertTrue(isinstance(provider, IDockerProvider))
        self.assertFalse(isinstance(provider, DockerClient))
        self.assertEqual('hypersh', provider.identifier())
        self.assertNotEqual(None, provider._get_auth())
        self.assertNotEqual({}, provider._get_auth())
        self.assertEqual('https://eu-central-1.hyper.sh/v1.23', provider.endpoint)

    def test_hypersh_client_with_region(self):
        provider = factory('hypersh', region='us-west-1')
        self.assertEqual('https://us-west-1.hyper.sh/v1.23', provider.endpoint)

    def test_not_found_provider(self):
        with self.assertRaises(TypeError) as context:
            factory('xxx')
        self.assertTrue('Not found docker client for provider xxx' in str(context.exception))


if __name__ == '__main__':
    unittest.main()
