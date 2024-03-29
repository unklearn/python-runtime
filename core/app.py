import tornado.web
import os
import code

from core.request_handlers import *
from core.config import get_current_config
from core.utils import ProcessRegistry


def make_app():
    config = get_current_config(os.environ.get('UNKLEARN_ENVIRONMENT_TYPE'))
    app = tornado.web.Application([
        # Ping handler
        (r"/ping/?", PingHandler),
        # Get runtime info
        (r"/info?", InfoRequestHandler),
        # Interactive REPL like
        (r"/interactive/?", InteractiveExecutionRequestHandler,
         dict(socketio=config.SOCKETIO,
              process_registry=ProcessRegistry(),
              console=code.InteractiveConsole())),
        # Creating files
        (r"/files/?(?P<file_path>[A-Z0-9a-z_\-.%]+)?", FilesHandler,
         dict(file_path_root=config.FILE_ROOT_DIR)),
        # File runs
        (r"/file-runs/?", FileExecutionHandler,
         dict(file_path_root=config.FILE_ROOT_DIR, socketio=config.SOCKETIO)),
        # Endpoint config dir can be separate, but here is the same
        (r"/endpoint-configs/?", EndpointConfigurationHandler,
         dict(config_path_root=config.ENDPOINT_CONFIG_ROOT_DIR)),
        # Endpoint execution runs
        (r"/endpoint-runs/?(?P<endpoint_name>[\w\-\d]+).*",
         EndpointExecutionHandler,
         dict(config_path_root=config.ENDPOINT_CONFIG_ROOT_DIR,
              file_path_root=config.FILE_ROOT_DIR))
    ])

    # Set config on app object
    app.config = config

    return app
