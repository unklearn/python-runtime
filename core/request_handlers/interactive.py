import tornado.web
from tornado.web import gen
from tornado.ioloop import IOLoop


class InteractiveExecutionRequestHandler(tornado.web.RequestHandler):
    """A request handler for executing code in an interactive fashion

    This is probably better handled by a xterm front-end with terminado backend.
    For now we are simply executing the shell commands by writing to a temporary
     file

    """

    def initialize(self, socketio=None, console_runner=None):
        # Create a version of socketio that routes to notebook
        self.socketio = socketio
        self.runner = console_runner

    def execute_interactive(self, code, cell_id, channel):
        """Execute the code provided in cell with specified id"""
        self.runner.submit(cell_id, code)

    def execute_code(self, cell_id, channel, code):
        self.execute_interactive(code, cell_id, channel)
        self.write('Ok')

    def get(self):
        # Get the arguments from code
        code = self.get_query_argument('code')
        channel = self.get_query_argument('channel')
        cell_id = self.get_query_argument('cellId')
        return self.execute_code(cell_id, channel, code)

    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        code = data['code']
        channel = data['channel']
        cell_id = data['cellId']
        return self.execute_code(cell_id, channel, code)
