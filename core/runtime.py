# encoding: utf-8
"""
Spawns a listener that is capable of executing python code.

The listener can execute code in several modes

a) REPL mode: using an instance of `code.InteractiveConsole`
b) File mode: execute code using `__main__` blocks and return output
c) Endpoint mode: Spawn an endpoint that blocks and waits for response. The stdout will
be redirected to cell log output.
d) Daemon mode, run long running processes with port forwarding setup to fe

"""
import os
import re
import sys
import code
import time
import asyncio
import contextlib
import json
import requests

import logging
import tornado.ioloop
import tornado.web
import tornado.escape

from io import StringIO
from subprocess import Popen, PIPE
from asyncio.subprocess import PIPE
from flask_socketio import SocketIO
from urllib.parse import urlparse

from core.config import get_current_config


__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'

# The config to load




class FileExecutionHandler(tornado.web.RequestHandler):
    """A request handler for executing python files"""
    def initialize(self, file_path_root):
        self.file_path_root = file_path_root

    def execute_file(self, file_path):
        """Execute the code provided by the file path"""
        p = Popen([sys.executable, file_path], env={
            # Module discovery
            'PYTHONPATH': self.file_path_root
        }, stdout=PIPE, stderr=PIPE, cwd=self.file_path_root)
        stdout, stderr = p.communicate()
        return stderr.decode('utf-8'), stdout.decode('utf-8')

    def get(self):
        file_path = self.get_query_argument('path')
        err, out = self.execute_file(secure_file_path(file_path, self.file_path_root))
        self.write(json.dumps({
            'error': err,
            'output': out
        }))

    def post(self):
        file_data = tornado.escape.json_decode(self.request.body)
        file_path = secure_file_path(file_data['filePath'], self.file_path_root)
        file_content = file_data['content']
        full_path = os.path.normpath(os.path.join(self.file_path_root, file_path))
        base_dir = os.path.dirname(full_path)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        return self.write(file_path)


class EndpointsHandler(tornado.web.RequestHandler):
    """Handle endpoint related requests"""

    def initialize(self, file_path_root):
        self.file_path_root = file_path_root

    def post(self):
        # An endpoint is like a dynamic route. We execute the endpoint by storing the config in a certain location.
        # Once the request is received, we will use the config to parse the request and execute the code within
        body = tornado.escape.json_decode(self.request.body)

        # The file we are wrapping in an endpoint
        file_path = secure_file_path(body['filePath'], self.file_path_root)

        config = body['config']

        config['filePath'] = file_path

        full_path = os.path.normpath(os.path.join(self.file_path_root, 'endpoints', '{}.config'.format(config['name'])))
        base_dir = os.path.dirname(full_path)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        # The endpoint configuration, which we will write to a file (or load from store later on)
        with open(full_path, 'w') as f:
            f.write(json.dumps(body['config']))
        return self.write('Ok')


class EndpointsExecutionHandler(tornado.web.RequestHandler):

    def initialize(self, file_path_root):
        self.file_path_root = file_path_root

    def write_error(self, status_code, **kwargs):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({
            'error': {
                'code': status_code,
                'message': self._reason
            }
        }))

    def _execute_endpoint(self, file_path):
        """Execute the code provided by the file path"""
        p = Popen([sys.executable, file_path], env={
            # Module discovery
            'PYTHONPATH': self.file_path_root
        }, stdout=PIPE, stderr=PIPE, cwd=self.file_path_root)
        stdout, stderr = p.communicate()
        return stderr.decode('utf-8'), stdout.decode('utf-8')

    def _get_config(self, endpoint_name):
        full_path = os.path.normpath(os.path.join(self.file_path_root, 'endpoints', '{}.config'.format(endpoint_name)))

        if not os.path.exists(full_path):
            raise tornado.web.HTTPError(404, reason='Missing endpoint configuration for {}. Please check if endpoint is defined.'.format(endpoint_name))
        with open(full_path, 'r') as f:
            return json.loads(f.read())

    def _write_endpoint_file(self, config):
        file_path = config['filePath']

        full_path = os.path.normpath(os.path.join(self.file_path_root, file_path))

        if not os.path.exists(full_path):
            raise tornado.web.HTTPError(404, reason='Missing endpoint configuration for {}. Please check if endpoint is defined.'.format(config['name']))

        with open(full_path, 'r') as f:
            content = f.read()

            # Use the server to parse the request arguments
            response = requests.post(SERVER_URI + '/api/v1/cells/internal-endpoints/parse', json={
                'config': config,
                'requestUri': self.request.uri
            })
            
            if response.status_code == 400:
                raise tornado.web.HTTPError(reason=response.json()['message'], status_code=400)
            elif response.status_code == 200:
                response_body = response.json()

                query_args = response_body['query']
                path_args = response_body['path']

                variable_sets = ['{} = "{}"'.format(k, v) if isinstance(v, str) else '{} = {}'.format(k, v) for k, v in path_args.items()]

                # Map them out in file as well
                variable_sets += ['{} = "{}"'.format(k, v) if isinstance(v, str) else '{} = {}'.format(k, v) for k, v in query_args.items()]

                file_postfix_content = '\n'.join(variable_sets)

                content += '\n' + file_postfix_content

                content += '\n\nprint({})'.format(config['signature'])

                # Write to endpoint specific file
                endpoint_file = full_path.replace('.py', '') + '--endpoint.py'
                with open(endpoint_file, 'w') as wf:
                    wf.write(content + '\n')

                return endpoint_file
            else:
                raise tornado.web.HTTPError(reason='Error while attempting to parse endpoint {}'.format(
                    re.sub(r'\r\n', '', response.text)))

    def get(self, endpoint_name):
        # Run the specified endpoint using signature
        config = self._get_config(endpoint_name)
        # Create endpoint_file and execute endpoint file

        endpoint_file = self._write_endpoint_file(config)

        err, output = self._execute_endpoint(endpoint_file)

        if err and len(err):
            self.set_status(500)
            return self.write(err)
        else:
            self.set_status(200)
            return self.write(output)

    def post(self, endpoint_name):
        config = self._get_config(endpoint_name)
        endpoint_file = self._write_endpoint_file(config)

        err, output = self._execute_endpoint(endpoint_file)

        if err and len(err):
            self.set_status(500)
            return self.write(err)
        else:
            self.set_status(200)
            return self.write(output)


class Python3REPLServer:
    """The Python3 REPl server"""
    def __init__(self, file_path_root='/tmp/code-files'):
        # Setup the console
        self.console = code.InteractiveConsole()

        # File path root will help with script execution
        self.file_path_root = file_path_root

        # Create file path root
        if not os.path.exists(file_path_root):
            os.makedirs(file_path_root)

        # Each endpoint will run in a separate Thread. Otherwise the event loop will block the new server endpoints.
        # We ideally expect a single kernel to have few endpoints. Creating lots of endpoints is not performant.
        # The server will proxy requests/responses to/from the endpoint processes.
        self._endpoint_threads = {}

    def execute_endpoint(self, cell_id, file_path):
        """Spawn a separate process that acts as a server endpoint."""
        # The server should maintain a state about the forked process.
        # If the code at file_path changes, the server must restart the process
        # so this is stateful
        raise NotImplementedError()

    def start(self):
        """Start a new REPL server"""
        config = get_current_config(os.environ.get('UNKLEARN_ENV_TYPE', 'production'))

        # Fire up the handlers
        app = tornado.web.Application([
            (r"/ping", PingHandler),
            (r"/repl", REPLExecutionHandler, dict(console=self.console)),
            (r"/file", FileExecutionHandler, dict(file_path_root=self.file_path_root)),
            (r"/endpoints", EndpointsHandler, dict(file_path_root=self.file_path_root)),
            (r"/endpoints/(?P<endpoint_name>[\w\-\d]+).*", EndpointsExecutionHandler, dict(file_path_root=self.file_path_root))
        ])
        app.listen(1111)
        logging.info('Started Python 3 Kernel...')
        tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    Python3REPLServer().start()
