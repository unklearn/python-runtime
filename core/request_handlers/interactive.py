import contextlib
from io import StringIO
import sys

import tornado.web
from tornado import gen
from tornado.ioloop import IOLoop

from core.constants import CELLS_NAMESPACE
from core.utils import ProcessRegistryObject, AsyncProcess, LocalSocketIO, \
    CellEventsSocket


class SocketIOStdoutStream(StringIO):
    """A stream that takes over stdout and emits via socket."""

    def __init__(self, socket, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket = socket
        self.original_stderr_write = sys.stderr.write
        self.called = False
        self.rc = 0

    @contextlib.contextmanager
    def redirect_stderr_write(self):
        # Use a stringIO object
        sys.stderr.write = self.write_error
        yield self
        sys.stderr_write = self.original_stderr_write
        self.close()

    def write(self, string, *args, **kwargs):
        if self.called is False:
            self.called = True
            self.socket.stdout([string])
            self.called = False
        else:
            sys.stdout.write(string)

    def write_error(self, string):
        self.socket.stderr([string])
        self.rc = -1

    def close(self, *args, **kwargs):
        super().close(*args, **kwargs)
        self.socket.done(self.rc)


class InteractiveExecutionRequestHandler(tornado.web.RequestHandler):
    """A request handler for executing code in an interactive fashion

    This is probably better handled by a xterm front-end with terminado backend.
    For now we are simply executing the shell commands by writing to a temporary
     file

    """

    def initialize(self, socketio=None, console=None, process_registry=None):
        self.console = console
        self.socketio = socketio
        self.process_registry = process_registry

    @gen.coroutine
    def execute_interactive(self, code, cell_id, channel):
        """Execute the code provided in cell with specified id"""
        # Execute code and on receiving input/output pipe them to server using
        # callback_url

        # Let notebook know cell is busy
        socketio = LocalSocketIO(self.socketio,
                                 namespace=CELLS_NAMESPACE,
                                 channel=channel)

        cell_socket = CellEventsSocket(socketio, cell_id)

        # Let notebook know cell is busy
        cell_socket.start()

        stream = SocketIOStdoutStream(cell_socket)

        import types
        import copy

        sys_copy = types.ModuleType('sys')

        for name, val in sys.__dict__.items():
            if name == 'stdout':
                sys_copy.__dict__['stdout'] = stream
            else:
                sys_copy.__dict__[name] = val

        original_import = __builtins__['__import__']

        builtins_copy = copy.copy(__builtins__)

        def custom_import(name, *args, **kwargs):
            if name == 'sys':
                return sys_copy
            return original_import(name, *args, **kwargs)

        builtins_copy['__import__'] = custom_import
        builtins_copy['print'] = lambda *args: cell_socket.stdout(
            [' '.join(args) + '\n'])

        # Redirect all print statements through stdout
        self.console.locals = {'__builtins__': builtins_copy}

        try:
            with stream.redirect_stderr_write():
                yield self.console.runcode(code)
        except KeyboardInterrupt as e:
            # InteractiveConsole may not always catch this!
            cell_socket.stderr([str(e)])
            cell_socket.done(-1)

    @gen.coroutine
    def execute_shell(self, code, cell_id, channel):
        socketio = LocalSocketIO(self.socketio,
                                 namespace=CELLS_NAMESPACE,
                                 channel=channel)

        cell_socket = CellEventsSocket(socketio, cell_id)

        # Let notebook know cell is busy
        cell_socket.start()

        # Create a process registry object if it does not exist
        pro = self.process_registry.get_process_info(cell_id)
        if pro is None:
            pro = ProcessRegistryObject(self.process_registry, cell_id=cell_id)
        else:
            # Kill process and children
            yield pro.kill()

        # Start process
        yield AsyncProcess(pro,
                           stdout_cb=cell_socket.stdout,
                           stderr_cb=cell_socket.stderr,
                           done_cb=cell_socket.done).start('/bin/bash', code)

    @gen.coroutine
    def execute_code(self, language, cell_id, channel, code):
        if language == 'shell':
            IOLoop.current().spawn_callback(self.execute_shell, code, cell_id,
                                            channel)
            self.write('Ok')
        else:
            # For console, we do not have process streams and we try synchronous
            # code execution
            yield self.execute_interactive(code, cell_id, channel)
            self.write('Ok')

    def get(self):
        code = self.get_query_argument('code')
        language = self.get_query_argument('language')
        channel = self.get_query_argument('channel')
        cell_id = self.get_query_argument('cellId')
        return self.execute_code(language, cell_id, channel, code)

    def post(self):
        language = self.get_query_argument('language')
        data = tornado.escape.json_decode(self.request.body)
        code = data['code']
        channel = data['channel']
        cell_id = data['cellId']
        return self.execute_code(language, cell_id, channel, code)
