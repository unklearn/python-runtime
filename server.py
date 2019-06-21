# coding: utf8
from tornado.ioloop import IOLoop

from core.app import make_app

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'

if __name__ == '__main__':
    app = make_app()
    app.listen(8888)
    IOLoop.current().start()
