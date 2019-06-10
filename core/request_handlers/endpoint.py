# coding: utf8
import os
import json
import tornado.web
import tornado.escape

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
