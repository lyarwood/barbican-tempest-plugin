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
from tempest import exceptions
from tempest.lib import decorators
from tempest import test

from barbican_tempest_plugin.tests.scenario import barbican_manager

CONF = config.CONF
LOG = logging.getLogger(__name__)


class ImageSigningTest(barbican_manager.BarbicanScenarioTest):

    @decorators.idempotent_id('4343df3c-5553-40ea-8705-0cce73b297a9')
    @test.services('compute', 'image')
    def test_signed_image_upload_and_boot(self):
        """Test that Nova boots a signed image.

        The test follows these steps:
            * Create an asymmetric keypair
            * Sign an image file with the private key
            * Create a certificate with the public key
            * Store the certificate in Barbican
            * Store the signed image in Glance
            * Boot the signed image
            * Confirm the instance changes state to Active
        """
        img_uuid = self.sign_and_upload_image()

        LOG.debug("Booting server with signed image %s", img_uuid)
        instance = self.create_server(name='signed_img_server',
                                      image_id=img_uuid,
                                      wait_until='ACTIVE')
        self.servers_client.delete_server(instance['id'])

    @decorators.idempotent_id('74f022d6-a6ef-4458-96b7-541deadacf99')
    @test.services('compute', 'image')
    def test_signed_image_upload_boot_failure(self):
        """Test that Nova refuses to boot an incorrectly signed image.

        If the create_server call succeeds instead of throwing an
        exception, it is likely that signature verification is not
        turned on.  To turn on signature verification, set
        verify_glance_signatures=True in the nova configuration
        file under the [glance] section.

        The test follows these steps:
            * Create an asymmetric keypair
            * Sign an image file with the private key
            * Create a certificate with the public key
            * Store the certificate in Barbican
            * Store the signed image in Glance
            * Modify the signature to be incorrect
            * Attempt to boot the incorrectly signed image
            * Confirm an exception is thrown
        """
        img_uuid = self.sign_and_upload_image()

        LOG.debug("Modifying image signature to be incorrect")
        metadata = {'img_signature': 'fake_signature'}
        self.compute_images_client.update_image_metadata(
            img_uuid, metadata
        )

        self.assertRaisesRegex(exceptions.BuildErrorException,
                               "Signature verification for the image failed",
                               self.create_server,
                               image_id=img_uuid)
