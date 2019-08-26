# coding: utf8
from tornado.ioloop import IOLoop

from core.app import AppFactory

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'

if __name__ == '__main__':
    app_f = AppFactory()
    app = app_f.make()

    try:
        print('Listening on port 8888')
        app.listen(8888)
        IOLoop.current().start()
    except KeyboardInterrupt:
        pass
    finally:
        app_f.cleanup()
