import tornado.web
import os
import asyncio
from contextlib import suppress

from core.request_handlers import *
from core.config import get_current_config
from core.runtime import InteractiveConsoleCodeRunner, CellLogRouter, QueuedProcessExecutorJobLoop


class AppFactory:
    """A wrapper class that provides an interface over a running flask app"""

    def __init__(self):
        self.ic_runner = None
        self.ps_job_loop = None

    def make(self):
        """Make a new instance of the app"""
        config = get_current_config(
            os.environ.get('UNKLEARN_ENVIRONMENT_TYPE'))

        # Buffer and write to Redis broker ?
        socket = config.SOCKETIO

        # Setup log router
        log_router = CellLogRouter(socket=socket)

        # Setup runners
        self.ic_runner = InteractiveConsoleCodeRunner(log_router)
        self.ps_job_loop = QueuedProcessExecutorJobLoop(log_router)

        # Start them
        self.ic_runner.start()
        self.ps_job_loop.start()

        app = tornado.web.Application(
            [
                # Ping handler
                (r"/ping/?", PingHandler),
                # Get runtime info
                (r"/info?", InfoRequestHandler),
                # Interactive REPL like
                (r"/interactive/?", InteractiveExecutionRequestHandler,
                 dict(socketio=config.SOCKETIO, console_runner=self.ic_runner)
                 ),
                # Creating files
                (r"/files/?(?P<file_path>[A-Z0-9a-z_\-.%]+)?", FilesHandler,
                 dict(file_path_root=config.FILE_ROOT_DIR)),
                # File runs
                (r"/file-runs/?", FileExecutionHandler,
                 dict(file_path_root=config.FILE_ROOT_DIR,
                      job_loop=self.ps_job_loop)),
                # Endpoint config dir can be separate, but here is the same
                (r"/endpoint-configs/?", EndpointConfigurationHandler,
                 dict(config_path_root=config.ENDPOINT_CONFIG_ROOT_DIR)),
                # Endpoint execution runs
                (r"/endpoint-runs/?(?P<endpoint_name>[\w\-\d]+).*",
                 EndpointExecutionHandler,
                 dict(config_path_root=config.ENDPOINT_CONFIG_ROOT_DIR,
                      file_path_root=config.FILE_ROOT_DIR))
            ],
            autoreload=getattr(config, 'AUTORELOAD', False))

        # Set config on app object
        app.config = config

        return app

    def cleanup(self):
        if self.ic_runner is not None:
            self.ic_runner.end()
        if self.ps_job_loop is not None:
            self.ps_job_loop.end()
        # Cancel all pending asyncio tasks
        loop = asyncio.get_event_loop()
        # Get pending tasks
        pending = asyncio.Task.all_tasks()
        for task in pending:
            task.cancel()
            # Now we should await task to execute it's cancellation.
            # Cancelled task raises asyncio.CancelledError that we can suppress:
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
