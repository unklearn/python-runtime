import tornado.web


class InteractiveExecutionRequestHandler(tornado.web.RequestHandler):
    """A request handler for executing code in an interactive fashion
    """

    def initialize(self, socketio=None, console_runner=None, job_loop=None):
        # Create a version of socketio that routes to notebook
        self.socketio = socketio
        self.runner = console_runner
        self.job_loop = job_loop

    def execute_interactive(self, code, cell_id, channel):
        """Execute the code provided in cell with specified id"""
        self.runner.submit(cell_id, code)

    def execute_python_code(self, cell_id, channel, code):
        self.execute_interactive(code, cell_id, channel)
        self.write('Ok')

    def execute_bash_code(self, cell_id, channel, code):
        self.job_loop.submit(cell_id, '/bin/bash', '-c', code)

    def execute_code(self, cell_id, channel, code, language):
        if language == 'shell':
            return self.execute_bash_code(cell_id, channel, code)
        elif language == 'python':
            return self.execute_python_code(cell_id, channel, code)

    def get(self):
        # Get the arguments from code
        code = self.get_query_argument('code')
        channel = self.get_query_argument('channel')
        cell_id = self.get_query_argument('cellId')
        language = self.get_query_argument('language')
        return self.execute_code(cell_id, channel, code, language)

    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        code = data['code']
        channel = data['channel']
        cell_id = data['cellId']
        language = self.get_query_argument('language')
        return self.execute_code(cell_id, channel, code, language)
