# coding: utf8
import os
import json
import re
import requests
import tornado.web
import tornado.escape
from subprocess import Popen, PIPE
import sys

from core.utils import secure_relative_file_path

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class EndpointConfigurationHandler(tornado.web.RequestHandler):
    """Create new endpoint configurations"""

    def initialize(self, config_path_root=None):
        """
        Parameters
        ----------
        config_path_root: str
            The root folder to use for storing endpoint configurations
        """
        self.config_path_root = config_path_root

    def validate_body_arguments(self, body):
        """Validate input args"""

        if not isinstance(body.get('config', None), dict):
            raise tornado.web.HTTPError(400, 'Endpoint config must be a dictionary')

        if not body.get('filePath', None):
            raise tornado.web.HTTPError(400, 'File path must be specified')

    def post(self):
        # An endpoint is like a dynamic route. We execute the endpoint by storing the config in a certain location.
        # Once the request is received, we will use the config to parse the request and execute the code within
        body = tornado.escape.json_decode(self.request.body)

        self.validate_body_arguments(body)

        # The file we are wrapping in an endpoint
        file_path = secure_relative_file_path(body['filePath'])

        # Add file path to config
        config = body['config']

        config['filePath'] = file_path

        name = config['name']
        full_path = os.path.normpath(os.path.join(self.config_path_root, '{}.config'.format(name)))

        base_dir = os.path.dirname(full_path)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # The endpoint configuration, which we will write to a file (or load from store later on)
        with open(full_path, 'w') as f:
            f.write(json.dumps(body['config'], sort_keys=True))

        # Return the sanitized config name
        return self.write('{}.config'.format(name))


class EndpointExecutionHandler(tornado.web.RequestHandler):
    """Handle execution of endpoints"""

    def initialize(self, file_path_root=None, config_path_root=None):
        self.file_path_root = file_path_root
        self.config_path_root = config_path_root

    def write_error(self, status_code, **kwargs):
        """Overwrite the error handler to send error code and reason"""
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({
            'error': {
                'code': status_code,
                'message': self._reason
            }
        }, indent=2))

    def _execute_endpoint(self, file_path):
        """Execute the code provided by the file path"""
        p = Popen([sys.executable, file_path], env={
            # Module discovery
            'PYTHONPATH': self.file_path_root
        }, stdout=PIPE, stderr=PIPE, cwd=self.file_path_root)
        stdout, stderr = p.communicate()
        return stderr.decode('utf-8'), stdout.decode('utf-8')

    def _get_config(self, endpoint_name):
        full_path = os.path.normpath(os.path.join(self.config_path_root, '{}.config'.format(endpoint_name)))

        if not os.path.exists(full_path):
            raise tornado.web.HTTPError(404,
                                        reason='Missing endpoint configuration for {}. '
                                               'Please check if endpoint is defined.'.format(endpoint_name))
        with open(full_path, 'r') as f:
            return json.loads(f.read())

    def _parse_endpoint_vars(self, config):
        app = self.application
        response = requests.post(app.config.SERVER_URI + '/api/v1/cells/internal-endpoints/parse', json={
            'config': config,
            'requestUri': self.request.uri
        })

        if response.status_code == 400:
            raise tornado.web.HTTPError(reason=response.json()['message'], status_code=400)
        elif response.status_code == 200:
            response_body = response.json()

            query_args = response_body['query']
            path_args = response_body['path']

            variable_sets = ['{} = "{}"'.format(k, v) if isinstance(v, str) else '{} = {}'.format(k, v) for k, v in
                             path_args.items()]

            # Map them out in file as well
            variable_sets += ['{} = "{}"'.format(k, v) if isinstance(v, str) else '{} = {}'.format(k, v) for k, v in
                              query_args.items()]

            file_postfix_content = '\n'.join(variable_sets)

            return file_postfix_content
        else:
            raise tornado.web.HTTPError(reason='Error while attempting to parse endpoint {}'.format(
                re.sub(r'\r\n', '', response.text)))

    def _write_endpoint_file(self, config):
        """Create endpoint file for execution"""
        file_path = config['filePath']

        full_path = os.path.normpath(os.path.join(self.file_path_root, file_path))

        if not os.path.exists(full_path):
            raise tornado.web.HTTPError(404, reason='The target file is missing. Please verify that the file {}'
                                                    'around which the endpoint is defined exists'.format(file_path,
                                                                                                         config['name'])
                                        )
        # Read the contents of the python file
        with open(full_path, 'r') as f:
            content = f.read()

            file_postfix_content = self._parse_endpoint_vars(config)

            content += '\n' + file_postfix_content

            content += '\n\nprint({})'.format(config['signature'])

            # Write to endpoint specific file
            endpoint_file = full_path.replace('.py', '') + '--endpoint.py'

            # Write the file to disk for execution
            with open(endpoint_file, 'w') as wf:
                wf.write(content + '\n')

            return endpoint_file

    def _handle_endpoint_execution(self, endpoint_name):
        # Run the specified endpoint using signature
        config = self._get_config(endpoint_name)
        # Create endpoint_file and execute endpoint file

        endpoint_file = self._write_endpoint_file(config)

        # Synchronous execution
        err, output = self._execute_endpoint(endpoint_file)

        if err and len(err):
            self.set_status(500)
            return self.write(err)
        else:
            self.set_status(200)
            return self.write(output)

    def get(self, endpoint_name):
        return self._handle_endpoint_execution(endpoint_name)

    def post(self, endpoint_name):
        return self._handle_endpoint_execution(endpoint_name)
