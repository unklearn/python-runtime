import json
import sys
import os
import tornado.escape
import tornado.web
from subprocess import Popen, PIPE

from core.utils import secure_relative_file_path
from core.constants import CellEvents, CellExecutionStatus, CELLS_NAMESPACE


class FilesHandler(tornado.web.RequestHandler):
    """A request handler for creating and fetching files"""

    def get_secure_filename(self, file_path):
        """Get secure file path relative to root directory"""
        return os.path.join(self.file_path_root,
                            secure_relative_file_path(file_path))

    def initialize(self, file_path_root=None):
        """Init called by tornado"""
        self.file_path_root = file_path_root

    def get(self, file_path=None):
        """Get a file given the file path"""
        file_path = self.get_secure_filename(file_path)
        if not os.path.exists(file_path):
            raise tornado.web.HTTPError(
                status_code=404,
                log_message='Cannot find a file with the file path: {}'.format(
                    file_path))
        with open(file_path, 'r') as f:
            contents = f.read()
        return self.write(contents)

    def post(self, file_path=None):
        """Create a new file based on file path and content"""
        # For POST, we take it from body and ignore path variable
        file_data = tornado.escape.json_decode(self.request.body)
        file_path = file_data.get('filePath', None)

        if not file_path:
            raise tornado.web.MissingArgumentError('filePath')

        file_content = file_data.get('content', None)

        if not file_content:
            raise tornado.web.MissingArgumentError('content')

        file_path = self.get_secure_filename(file_path)

        base_dir = os.path.dirname(file_path)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        # Send back the secure relative path
        return self.write(secure_relative_file_path(file_data['filePath']))


class FileExecutionHandler(tornado.web.RequestHandler):
    """A request handler that takes care of executing python files."""

    def get_secure_filename(self, file_path):
        """Get secure file path relative to root directory"""
        return os.path.join(self.file_path_root,
                            secure_relative_file_path(file_path))

    def initialize(self, file_path_root=None, job_loop=None):
        """Init called by tornado"""
        self.file_path_root = file_path_root
        self.job_loop = job_loop

    def execute_python_file(self, cell_id, file_path):
        self.job_loop.submit(cell_id, sys.executable, '-u', file_path, env={
            'PYTHONPATH': self.file_path_root
        })

    def validate_post_body(self, file_data):
        """Validate the necessary arguments"""
        for arg in ['cellId', 'channel', 'filePath']:
            d = file_data.get(arg, None)
            if d is None or (d and not len(d)):
                raise tornado.web.MissingArgumentError(arg)

        file_path = file_data['filePath']
        file_path = self.get_secure_filename(file_path)

        if not file_path.endswith('.py'):
            raise tornado.web.HTTPError(
                400, 'Cannot execute a file whose extension is not .py')

        if not os.path.exists(file_path):
            raise tornado.web.HTTPError(
                404, 'Cannot find file at {}'.format(file_path))

    def post(self):
        """Run the file at the given file path"""
        file_data = tornado.escape.json_decode(self.request.body)

        self.validate_post_body(file_data)

        file_path = file_data.get('filePath', None)
        cell_id = file_data.get('cellId', None)
        channel = file_data.get('channel', None)

        file_path = self.get_secure_filename(file_path)
        self.execute_python_file(cell_id, file_path)
        return self.write('Ok')
