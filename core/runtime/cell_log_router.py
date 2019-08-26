# coding: utf8
import threading
import sys
import os
from contextlib import contextmanager
from io import StringIO
from queue import Queue as RegularQueue
from multiprocessing import Queue

__author__ = 'Tharun Mathew Paul (tharun@bigpiventures.com)'


class StdoutSocket:
    def __init__(self):
        self.orig = sys.stdout

    def emit(self, event, data):
        self.orig.write(str(event) + str(data) + '\n')
        self.orig.flush()


class CellLogRouter:
    """Create a new routing mechanism for cell based logs

    Parameters
    ----------
    socket: Socket, optional
        An object with an emit method that is called with cell specific
        output. If omitted, it prints to stdout.

        Warning: Do not use StdoutSocket if sys.stdout is being replaced.
        This can cause infinte loops. It will throw an Error

    queue: Queue, optional
        Optional queue that allows interprocess communication if the
        capture_logs command is called from another process !


    Usage
    -----
    >>> router = BaseCellLogRouter(socket)

    >>> router.capture_logs('cell_id', stdout=<stdout_stream>, stderr=<stderr_stream>)

    If you want to instead capture sys.stdout, specify
    >>> router.capture_logs('cell_id', use_sys_streams=True)
    """

    def __init__(self, socket=None, queue=None):
        self.socket = socket or StdoutSocket()
        self._queue = queue or Queue()
        self._pid = os.getpid()

    def _spawn_output_listener(self, queue):
        """Spawn a new listener for getting output from queue."""
        while True:
            [cell_id, key, log] = queue.get()
            # Route to appropriate socket & cell
            self.socket.emit('log', {'id': cell_id, key: log})

    def _read_stream(self, stream, cell_id, key):
        for line in iter(stream.readline, ''):
            self._queue.put_nowait([cell_id, key, line])

    @contextmanager
    def capture_logs(self,
                     cell_id,
                     stdout=None,
                     stderr=None,
                     use_sys_streams=True):
        """Capture the log output from a given stdout and stderr"""
        o_t = threading.Thread(target=self._spawn_output_listener,
                               args=(self._queue, ))
        o_t.start()
        sys_out = None
        sys_err = None
        # Start two new threads, one to capture stdout and another to capture
        # stderr
        if use_sys_streams is True:
            if isinstance(self.socket, StdoutSocket):
                # Must be a different process, otherwise infinite loops!
                if os.getpid() == self._pid:
                    raise RuntimeError(
                        'StdoutSocket cannot be used if running in the same '
                        'process with sys streams')
            # Overwrite sys streams
            sys_out = sys.stdout
            sys_err = sys.stderr
            stdout_r, stdout_w = os.pipe()
            stderr_r, stderr_w = os.pipe()
            sys.stdout = os.fdopen(stdout_w, 'w', buffering=1)
            sys.stderr = os.fdopen(stderr_w, 'w', buffering=1)
            stdout = os.fdopen(stdout_r, 'r')
            stderr = os.fdopen(stderr_r, 'r')
        try:
            t1 = threading.Thread(target=self._read_stream,
                                  args=(stdout, cell_id, 'out'))
            t2 = threading.Thread(target=self._read_stream,
                                  args=(stderr, cell_id, 'err'))
            t1.start()
            t2.start()
            yield
        finally:
            if sys_out is not None:
                sys.stdout = sys_out
            if sys_err is not None:
                sys.stderr = sys_err
