# coding: utf8
import code
import os
import signal
from multiprocessing import Queue, Value, Process

from .cell_log_router import CellLogRouter

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class InteractiveConsoleCodeRunner:
    """A wrapper class that runs an interactive console in a separate
    multiprocessing.Process and communicates via Queue.

    Items are put in queue, and code runner will pick them off from queue

    Parameters
    ----------
    log_router: CellLogRouter
        An instance of cell level router that routes output to cell specific
        socket and room

    Attributes
    -----------
    _queue: Queue
        The queue to submit code to

    status: Value
        Integer shared value indicating if console is busy or not

    _router: CellLogRouter
        An instance of cell level router that routes output to cell specific
        socket and room
    """

    def __init__(self, log_router=None):
        self._queue = Queue()
        self.status = Value('i', -1)
        self._router = log_router

    def _run_console(self, status):
        """Run the console code runner in a loop"""
        console = code.InteractiveConsole()
        while True:
            try:
                [cell_id, code_str] = self._queue.get()
                with self._router.capture_logs(cell_id, use_sys_streams=True):
                    try:
                        status.value = 1
                        console.runcode(code_str)
                    finally:
                        status.value = -1
            except EOFError:
                # End of queue, pipe
                pass

    def _start_guard(self):
        if not hasattr(self, '_process'):
            raise RuntimeError('Process has not started yet.')

    """
    Public methods
    """

    def start(self):
        p = Process(target=self._run_console, args=(self.status, ))
        p.start()
        self._process = p

    def is_busy(self):
        """Check if console is busy"""
        return self.status.value == 1

    def submit(self, cell_id, code_str):
        self._start_guard()
        if self.is_busy():
            raise Exception('code console is busy!')
        else:
            self._queue.put_nowait([cell_id, code_str])

    def interrupt(self):
        """Send interrupt signal"""
        self._start_guard()
        pid = self._process.pid
        os.kill(pid, signal.SIGINT)

    def end(self):
        self._start_guard()
        self._queue.close()
        self._process.terminate()
