# coding: utf8
import os
import threading
import subprocess
import signal
import sys
from multiprocessing import Queue, Process, Value

__author__ = 'Tharun Mathew Paul (tharun@bigpiventures.com)'


class QueuedProcessExecutorJobLoop:
    """Runs a simple loop that processes requests for running commands in cells.

    Each cell in the runbook can submit commands to be run in the job loop.
    In this case, the cell behaves like a Tab in the terminal, unless you
    kill the existing long running process, new commands are not accepted.

    By default this is the behaviour, but in the future, we want a version
    wherein new commands are stored in buffer and executed.

    The job loop accepts a log router that routes the process stderr and
    stdout to appropriate cell level socket. The format for logs is specified
    by the router itself.

    Parameters
    ----------
    log_router: CellLogRouter, optional
        An instance of CellLogRouter that routes logs for each cell to socket
        rooms. If not provided, it will default and print to stdout.

    Attributes
    ----------
    _request_queue: Queue
        A queue that maintains submitted requests

    _output_queue: Queue
        A queue that keeps the items from various processes. It will be routed
        by log router

    _cell_status_map: dict
        A dict that maps the status of a cell to a numeric value. If the value
        is -1, then it means cell is IDLE, otherwise the value is the id of the
        process it is executing.

    _router: CellLogRouter
        An instance of CellLogRouter that routes logs for each cell to socket
        rooms.


    Examples
    --------
    >>> job_loop = QueuedProcessExecutorJobLoop(log_router=..)
    >>> job_loop.start()
    >>> job_loop.submit('cell_0', [sys.executable, '-u', 'path/to/file'])
    >>> job_loop.submit('cell_1', ['ls', '-al'])
    >>> job_loop.submit('cell_0', ['ls', '-al'])
    >>> # throws error if cell_0 is still executing "path/to/file"
    >>> job_loop.stop()

    When job_loop is no longer needed, shut it down by calling end.
    """

    def __init__(self, log_router=None):
        self._request_queue = Queue()
        self._output_queue = Queue()
        self._cell_status_map = {}
        self._router = log_router

    def _start_listener(self):
        """Start a new listener process that waits for inputs"""
        self._listener = Process(target=self._run_listener,
                                 args=(self._request_queue, ))
        self._listener.start()

    def _spawn_output_listener(self, queue):
        """Spawn a new listener for getting output from queue."""
        while True:
            item = queue.get()
            # Route to appropriate socket & cell
            self._route_item(item)

    def _route_item(self, item):
        """Parse and route to correct socket"""
        if self._router is None:
            print(item)
        else:
            self._router.route(item)

    def _get_pid_for_cid(self, cid):
        pid = self._cell_status_map.get(cid, None)
        if pid is not None:
            return pid.value
        return None

    def _run_listener(self, queue):
        """Run a listener loop waiting for items from queue"""
        # Start a new thread to listen to child process output and stderr
        o_t = threading.Thread(target=self._spawn_output_listener,
                               args=(self._output_queue, ))
        o_t.start()
        # Do not join output queue thread because it will block.
        while True:
            item = queue.get()
            t = threading.Thread(target=self._run_subprocess, args=item)
            t.start()

    def _read_stream(self, stream, key):
        for line in iter(stream.readline, b''):
            self._publish(key, line)

    def _publish(self, key, line):
        """Publish a line of output from"""
        self._output_queue.put_nowait(key.encode('utf-8') + b':' + line)

    def _start_readers(self, cell_id, process):
        t1 = threading.Thread(target=self._read_stream,
                              args=(process.stdout, '{}:out'.format(cell_id)))
        t2 = threading.Thread(target=self._read_stream,
                              args=(process.stderr, '{}:err'.format(cell_id)))
        t1.start()
        t2.start()
        # Start and join the threads
        t1.join()
        t2.join()

    def _run_subprocess(self, cell_id, *args):
        status = self._cell_status_map.get(cell_id, None)
        if status is not None and status.value != -1:
            raise Exception('cell {} is already busy with pid {}'.format(
                cell_id, status.value))
        process = None
        try:
            process = subprocess.Popen(*args,
                                       env={},
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            self._cell_status_map[cell_id] = Value('i', process.pid)
            # Now we need either asyncio or threaded reads that push to our socket.
            self._start_readers(cell_id, process)
        finally:
            # Here we reset cell status
            if process is not None:
                process.terminate()
            self._cell_status_map[cell_id] = Value('i', -1)

    """
    Public methods
    """

    def start(self):
        """Start the job queue listener"""
        yield self._start_listener()

    def submit(self, cell_id, args):
        """Submit a new job for given cell id"""
        if not hasattr(self, '_listener'):
            raise RuntimeError('Instances of {} must be started via `start` '
                               'method before submit is called'.format(
                                   __class__.__name__))
        self._request_queue.put_nowait([cell_id, args])

    def interrupt(self, cid):
        """Interrupt the running cell's process"""
        # find process for cid, by passing to queue
        pid = self._get_pid_for_cid(cid)
        if pid is not None:
            # We will not wait here.
            os.kill(pid, signal.SIGINT)

    def kill(self, cid):
        """Kill the cell's process"""
        pid = self._get_pid_for_cid(cid)
        if pid is not None:
            os.kill(pid, signal.SIGKILL)

    def end(self):
        """Gracefully exit"""
        # We kill any orphan processes
        for cid in self._cell_status_map.keys():
            if self._cell_status_map[cid].value != -1:
                pid = self._get_pid_for_cid(cid)
                if pid is not None:
                    self.kill(pid)
        if hasattr(self, '_listener'):
            self._listener.terminate()
