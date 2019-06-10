import pytest
import json
import os

from support.base_test_handler import TestHandlerBase

from core.constants import CellEvents, CellExecutionStatus, CELLS_NAMESPACE


@pytest.mark.handlers
@pytest.mark.integration
class TestFilesHandler(TestHandlerBase):

    def assert_file_and_remove(self, file_path, content=None, remove=True, response=None):
        app = self.get_app()
        file_path = os.path.join(app.config.FILE_ROOT_DIR, file_path)
        assert os.path.exists(file_path)

        if response:
            body = response.body.decode('utf-8')

            assert body == file_path

        if content:
            with open(file_path, 'r') as f:
                assert f.read() == content

        if remove:
            os.unlink(file_path)

    def test_creating_files(self):
        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'content': 'print("Hello")'
                          }), follow_redirects=False)

        assert resp.code == 200
        # Assert that file exists
        self.assert_file_and_remove('modules/test.py', 'print("Hello")', response=resp)

    def test_file_overwrite(self):
        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'content': 'print("Hello")'
                          }), follow_redirects=False)

        assert resp.code == 200
        # Assert that file exists
        self.assert_file_and_remove('modules/test.py', content='print("Hello")', remove=False, response=resp)

        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'content': 'print("World")'
                          }), follow_redirects=False)

        assert resp.code == 200
        self.assert_file_and_remove('modules/test.py', content='print("World")', response=resp)

    def test_missing_file_arguments(self):
        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': None,
                              'content': 'print("Hello")'
                          }), follow_redirects=False)

        assert resp.code == 400

        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py'
                          }), follow_redirects=False)

        assert resp.code == 400

    def test_dangerous_file_path(self):
        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': '~/.ssh/config',
                              'content': 'Bad code'
                          }), follow_redirects=False)

        assert resp.code == 200

        self.assert_file_and_remove('.ssh/config', 'Bad code', response=resp)

        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': '../../../..ssh/config',
                              'content': 'Bad code'
                          }), follow_redirects=False)

        assert resp.code == 200

        # Assert that file exists
        self.assert_file_and_remove('ssh/config')

        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': '../../../../ssh/config',
                              'content': 'Bad code'
                          }), follow_redirects=False)

        assert resp.code == 200
        # Assert that file exists
        self.assert_file_and_remove('ssh/config', response=resp)

    def test_fetching_file_with_encoded_file_name(self):
        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'content': 'print("Hello")'
                          }), follow_redirects=False)

        assert resp.code == 200

        resp = self.fetch('/files/modules%2Ftest.py', method='GET')

        assert resp.code == 200
        assert resp.body == b'print("Hello")'

    def test_fetching_file_with_unencoded_file_name(self):
        resp = self.fetch('/files',
                          method='POST',
                          body=json.dumps({
                              'filePath': 'modules/test.py',
                              'content': 'print("Hello")'
                          }), follow_redirects=False)

        assert resp.code == 200

        resp = self.fetch('/files/modules/test.py', method='GET')

        assert resp.code == 404
        self.assert_file_and_remove('modules/test.py')

    def test_non_existent_file(self):
        resp = self.fetch('/files/modules%2Ftest.py', method='GET')

        assert resp.code == 404