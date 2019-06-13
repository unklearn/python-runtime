# coding: utf8
import pytest
import json
import os

from support.base_test_handler import TestHandlerBase

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


@pytest.mark.handlers
@pytest.mark.integration
class TestEndpointConfigurationHandler(TestHandlerBase):

    def assert_file_and_remove(self, file_path, config=None, remove=True, response=None):
        app = self.get_app()
        full_path = os.path.normpath(os.path.join(app.config.ENDPOINT_CONFIG_ROOT_DIR, '{}.config'.format(config['name'])))
        assert os.path.exists(full_path)

        if response and config:
            body = response.body.decode('utf-8')

            assert body == '{}.config'.format(config['name'])

        if config:
            with open(full_path, 'r') as f:
                assert f.read() == json.dumps({**config, ** {
                    'filePath': file_path
                }}, sort_keys=True)

        if remove:
            os.unlink(full_path)

    def test_endpoint_config_creation(self):
        resp = self.fetch('/endpoint-configs',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'config': {
                                  'name': 'test-endpoint',
                                  'path': '<str:day>'
                              }
                          }), follow_redirects=False)

        assert resp.code == 200
        # Assert that file exists
        self.assert_file_and_remove('modules/test.py', {
            'path': '<str:day>',
            'name': 'test-endpoint',
            'filePath': 'modules/test.py'
        }, response=resp)

    def test_endpoint_config_overwrite(self):
        resp = self.fetch('/endpoint-configs',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'config': {
                                  'name': 'test-endpoint',
                                  'path': '<str:day>'
                              }
                          }), follow_redirects=False)

        assert resp.code == 200
        # Assert that file exists
        self.assert_file_and_remove('modules/test.py', {
            'path': '<str:day>',
            'name': 'test-endpoint',
            'filePath': 'modules/test.py'
        }, response=resp, remove=False)

        resp = self.fetch('/endpoint-configs',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'config': {
                                  'path': '<str:day2>',
                                  'name': 'test-endpoint',
                              }
                          }), follow_redirects=False)

        assert resp.code == 200
        # Assert that file exists
        self.assert_file_and_remove('modules/test.py', {
            'path': '<str:day2>',
            'name': 'test-endpoint',
            'filePath': 'modules/test.py'
        }, response=resp)

    def test_missing_file_arguments(self):
        resp = self.fetch('/endpoint-configs',
                          method='POST',
                          body=json.dumps({
                              'filePath': None,
                              'config': None
                          }), follow_redirects=False)

        assert resp.code == 400

        resp = self.fetch('/endpoint-configs',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py'
                          }), follow_redirects=False)

        assert resp.code == 400

        resp = self.fetch('/endpoint-configs',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'config': 'test'
                          }), follow_redirects=False)

        assert resp.code == 400

    def test_dangerous_file_path(self):
        resp = self.fetch('/endpoint-configs',
                          method='POST',
                          body=json.dumps({
                              'filePath': '~/.ssh/config',
                              'config': {
                                  'path': '<str:day2>',
                                  'name': 'test-endpoint'
                              }
                          }), follow_redirects=False)

        assert resp.code == 200

        self.assert_file_and_remove('.ssh/config', config={
            'path': '<str:day2>',
            'filePath': '.ssh/config',
            'name': 'test-endpoint'
        }, response=resp)

        resp = self.fetch('/endpoint-configs',
                          method='POST',
                          body=json.dumps({
                              'filePath': '../../../..ssh/config',
                              'config': {
                                  'path': '<str:day2>',
                                  'name': 'test-endpoint'
                              }
                          }), follow_redirects=False)

        assert resp.code == 200

        # Assert that file exists
        self.assert_file_and_remove('ssh/config', config={
            'path': '<str:day2>',
            'filePath': 'ssh/config',
            'name': 'test-endpoint'
        }, response=resp)
