import os
import contextlib
import code
from io import StringIO

import tornado.web
from subprocess import PIPE
import subprocess
from tornado import gen

from core.stream import capture_logs
from core.constants import CellEvents, CellExecutionStatus, CELLS_NAMESPACE
from core.utils import create_temporary_shell_file


class InteractiveExecutionRequestHandler(tornado.web.RequestHandler):
    """A request handler for executing code in an interactive fashion

    This is probably better handled by a xterm front-end with terminado backend.
    For now we are simply executing the shell commands by writing to a temporary file

    """

    def initialize(self, socketio):
        self.console = code.InteractiveConsole()
        self.socketio = socketio

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
        self.socketio.emit(CellEvents.RESULT, {
            'id': cell_id,
            'output': out,
            'error': err,
        },
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
        # Let notebook know cell is busy
        self.socketio.emit(CellEvents.START_RUN, {
            'id': cell_id,
            'status': CellExecutionStatus.BUSY
        },
                           room=channel,
                           namespace=CELLS_NAMESPACE)
        with create_temporary_shell_file(cell_id, code) as filename:
            process = subprocess.run(['bash', filename],
                                     stdout=PIPE,
                                     stderr=PIPE)
            out, err = process.stdout, process.stderr
            self.socketio.emit(
                CellEvents.RESULT, {
                    'id': cell_id,
                    'output': out.decode('utf-8'),
                    'error': err.decode('utf-8').replace(filename, '-bash'),
                },
                room=channel,
                namespace=CELLS_NAMESPACE)
        self.socketio.emit(CellEvents.END_RUN, {
            'id':
            cell_id,
            'status':
            CellExecutionStatus.ERROR if
            (err and len(err)) else CellExecutionStatus.DONE
        },
                           room=channel,
                           namespace=CELLS_NAMESPACE)

    @gen.coroutine
    def execute_code(self, language, cell_id, channel, code):
        if language == 'shell':
            yield self.execute_shell(code, cell_id, channel)
            self.write('Ok')
        else:
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
