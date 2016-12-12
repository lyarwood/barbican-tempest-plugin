# Copyright 2016 SAP SE
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import functools

from tempest import config
from tempest import test

from barbican_tempest_plugin import clients

CONF = config.CONF

# NOTE(dane-fichter): We need to track resource types for cleanup.
RESOURCE_TYPES = ['secret']


def _get_uuid(href):
    return href.split('/')[-1]


def creates(resource):
    """Decorator that adds resource UUIDs to queue for cleanup"""

    def decorator(f):
        @functools.wraps(f)
        def wrapper(cls, *args, **kwargs):
            resp = f(cls, *args, **kwargs)
            if resource == 'secret':
                uuid = _get_uuid(resp['secret_ref'])
            cls.created_objects[resource].add(uuid)
            return resp
        return wrapper
    return decorator


class BaseKeyManagerTest(test.BaseTestCase):
    """Base class for all api tests."""

    # Why do I have to be an admin to create secrets? No idea...
    credentials = ('admin', )
    client_manager = clients.Clients
    created_objects = {}

    @classmethod
    def setup_clients(cls):
        super(BaseKeyManagerTest, cls).setup_clients()
        os = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.secret_client = os.secret_v1.SecretClient(service='key-manager')

    @classmethod
    def resource_setup(cls):
        super(BaseKeyManagerTest, cls).resource_setup()
        for resource in RESOURCE_TYPES:
            cls.created_objects[resource] = set()

    @classmethod
    def resource_cleanup(cls):
        try:
            for secret_uuid in cls.created_objects['secret']:
                cls.delete_secret(secret_uuid)
        finally:
            super(BaseKeyManagerTest, cls).resource_cleanup()

    @classmethod
    @creates('secret')
    def create_secret(cls, **kwargs):
        return cls.secret_client.create_secret(**kwargs)

    @classmethod
    def delete_secret(cls, uuid):
        cls.created_objects['secret'].remove(uuid)
        return cls.secret_client.delete_secret(uuid)