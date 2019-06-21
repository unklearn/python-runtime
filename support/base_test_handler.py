from tornado.testing import AsyncHTTPTestCase
from core.app import make_app

app = make_app()


class TestHandlerBase(AsyncHTTPTestCase):
    def setUp(self):
        super(TestHandlerBase, self).setUp()
        self.socketio = app.config.SOCKETIO

    def get_app(self):
        return app  # this is the global app that we created above

    def tearDown(self):
        self.socketio._queue = []
