import time
from uuid import uuid4

from hypersh_client.main.hypersh import HypershClient


if __name__ == '__main__':
    client = HypershClient()
    client.remove_all_containers_with_image('digiology/selenium_node')
    success, containers = client.get_containers()
    success, fips = client.get_fips()
    name = 'seleniumnode' + uuid4().hex[:7]
    success, container_id = client.create_container('digiology/selenium_node', name=name)
    time.sleep(6)
    success, containers = client.get_containers()
    assert (name in [c['name'] for c in containers]) is True
