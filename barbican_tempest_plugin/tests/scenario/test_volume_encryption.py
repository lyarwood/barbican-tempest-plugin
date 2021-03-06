# Copyright (c) 2017 Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log as logging
from tempest import config
from tempest.lib import decorators
from tempest import test

from barbican_tempest_plugin.tests.scenario import barbican_manager

CONF = config.CONF
LOG = logging.getLogger(__name__)


class VolumeEncryptionTest(barbican_manager.BarbicanScenarioTest):

    """The test suite for encrypted cinder volumes

    This test is for verifying the functionality of encrypted cinder volumes.
    For both LUKS and cryptsetup encryption types, this test performs
    the following:
        * Creates an image in Glance
        * Boots an instance from the image
        * Creates an encryption type (as admin)
        * Creates a volume of that encryption type (as a regular user)
        * Attaches and detaches the encrypted volume to the instance
    NOTE (dane-fichter): These tests use a key stored in Barbican, unlike
    the original volume encryption scenario in Tempest.
    """

    @classmethod
    def skip_checks(cls):
        super(VolumeEncryptionTest, cls).skip_checks()
        if not CONF.compute_feature_enabled.attach_encrypted_volume:
            raise cls.skipException('Encrypted volume attach is not supported')

    def create_encrypted_volume(self, encryption_provider, volume_type):
        volume_type = self.create_volume_type(name=volume_type)
        self.create_encryption_type(type_id=volume_type['id'],
                                    provider=encryption_provider,
                                    key_size=256,
                                    cipher='aes-xts-plain64',
                                    control_location='front-end')
        return self.create_volume(volume_type=volume_type['name'])

    def attach_detach_volume(self, server, volume, keypair):
        # Attach volume
        attached_volume = self.nova_volume_attach(server, volume)

        # Write a timestamp to volume
        server_ip = self.get_server_ip(server)
        timestamp = self.create_timestamp(
            server_ip,
            dev_name=CONF.compute.volume_device_name,
            private_key=keypair['private_key']
        )
        timestamp2 = self.get_timestamp(
            server_ip,
            dev_name=CONF.compute.volume_device_name,
            private_key=keypair['private_key']
        )
        self.assertEqual(timestamp, timestamp2)

        # Detach volume
        self.nova_volume_detach(server, attached_volume)

    @decorators.idempotent_id('89165fb4-5534-4b9d-8429-97ccffb8f86f')
    @test.services('compute', 'volume', 'image')
    def test_encrypted_cinder_volumes_luks(self):
        img_uuid = self.sign_and_upload_image()
        LOG.info("Creating keypair and security group")
        keypair = self.create_keypair()
        security_group = self._create_security_group()
        server = self.create_server(
            name='signed_img_server',
            image_id=img_uuid,
            key_name=keypair['name'],
            security_groups=[{'name': security_group['name']}],
            wait_until='ACTIVE'
        )
        volume = self.create_encrypted_volume('nova.volume.encryptors.'
                                              'luks.LuksEncryptor',
                                              volume_type='luks')
        self.attach_detach_volume(server, volume, keypair)

    @decorators.idempotent_id('cbc752ed-b716-4727-910f-956ccf965723')
    @test.services('compute', 'volume', 'image')
    def test_encrypted_cinder_volumes_cryptsetup(self):
        img_uuid = self.sign_and_upload_image()
        LOG.info("Creating keypair and security group")
        keypair = self.create_keypair()
        security_group = self._create_security_group()

        server = self.create_server(
            name='signed_img_server',
            image_id=img_uuid,
            key_name=keypair['name'],
            security_groups=[{'name': security_group['name']}],
            wait_until='ACTIVE'
        )
        volume = self.create_encrypted_volume('nova.volume.encryptors.'
                                              'cryptsetup.CryptsetupEncryptor',
                                              volume_type='cryptsetup')
        self.attach_detach_volume(server, volume, keypair)
