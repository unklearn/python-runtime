# coding: utf8
import tornado.web

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class PingHandler(tornado.web.RequestHandler):
    """A request handler for health status checks"""

    def get(self):
        return self.write('pong')
