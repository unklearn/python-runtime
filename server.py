# coding: utf8
import asyncio
from contextlib import suppress

from tornado.ioloop import IOLoop

from core.app import make_app

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'

if __name__ == '__main__':
    app = make_app()
    app.listen(8888)
    try:
        IOLoop.current().start()
    except KeyboardInterrupt:
        pass
    finally:
        loop = asyncio.get_event_loop()
        # Get pending tasks
        pending = asyncio.Task.all_tasks()
        for task in pending:
            task.cancel()
            # Now we should await task to execute it's cancellation.
            # Cancelled task raises asyncio.CancelledError that we can suppress:
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
