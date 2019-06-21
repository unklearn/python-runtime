import contextlib
import os
from io import StringIO

import tornado.web
from tornado import gen
from tornado.ioloop import IOLoop

from core.constants import CellEvents, CellExecutionStatus, CELLS_NAMESPACE
from core.utils import ProcessRegistryObject, AsyncProcess, LocalSocketIO, CellEventsSocket


class InteractiveExecutionRequestHandler(tornado.web.RequestHandler):
    """A request handler for executing code in an interactive fashion

    This is probably better handled by a xterm front-end with terminado backend.
    For now we are simply executing the shell commands by writing to a temporary file

    """

    def initialize(self, socketio=None, console=None, process_registry=None):
        self.console = console
        self.socketio = socketio
        self.process_registry = process_registry

    @gen.coroutine
    def execute_interactive(self, code, cell_id, channel):
        """Execute the code provided in cell with specified id"""
        # Execute code and on receiving input/output pipe them to server using callback_url
        out = StringIO()
        err = StringIO()

        # Let notebook know cell is busy
        self.socketio.emit(CellEvents.START_RUN, {
            'id': cell_id,
            'status': CellExecutionStatus.BUSY
        },
                           room=channel,
                           namespace=CELLS_NAMESPACE)

        status = CellExecutionStatus.DONE
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(
                    err):
                yield self.console.runcode(code)
        except SyntaxError:
            self.console.showsyntaxerror()
            status = CellExecutionStatus.ERROR
        except:
            self.console.showtraceback()
            status = CellExecutionStatus.ERROR

        out = out.getvalue()
        err = err.getvalue()
        res = {'id': cell_id}
        if err and len(err):
            res['error'] = err

        if out and len(out):
            res['output'] = out

        self.socketio.emit(CellEvents.RESULT,
                           res,
                           room=channel,
                           namespace=CELLS_NAMESPACE)

        if err and len(err):
            status = CellExecutionStatus.ERROR

        # Signal execution end
        self.socketio.emit(CellEvents.END_RUN, {
            'id': cell_id,
            'status': status
        },
                           room=channel,
                           namespace=CELLS_NAMESPACE)

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
            # For console, we do not have process streams and we try synchronous code execution
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
