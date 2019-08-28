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
        self._cell_status_map = {}
        self._router = log_router

    def _start_listener(self):
        """Start a new listener process that waits for inputs"""
        self._listener = Process(target=self._run_listener,
                                 args=(self._request_queue, ))
        self._listener.start()

    def _get_pid_for_cid(self, cid):
        pid = self._cell_status_map.get(cid, None)
        if pid is not None:
            return pid.value
        return None

    def _run_listener(self, queue):
        """Run a listener loop waiting for items from queue"""
        # Do not join output queue thread because it will block.
        while True:
            item = queue.get()
            t = threading.Thread(target=self._run_subprocess, args=(item[0], item[1], item[2]))
            t.start()

    def _read_stream(self, stream, cell_id, key):
        for line in iter(stream.readline, b''):
            self._router.publish(cell_id, key, line)

    def _start_readers(self, cell_id, process):
        t1 = threading.Thread(target=self._read_stream,
                              args=(process.stdout, cell_id, 'out'))
        t2 = threading.Thread(target=self._read_stream,
                              args=(process.stderr, cell_id, 'err'))
        t1.start()
        t2.start()
        # Start and join the threads
        t1.join()
        t2.join()

    def _run_subprocess(self, cell_id, args, kwargs):
        status = self._cell_status_map.get(cell_id, None)
        if status is not None and status.value != -1:
            msg = 'cell {} is already busy with pid {}'.format(
                cell_id, status.value)
            self._router.publish(
                cell_id,
                'err',
                msg
            )
            raise Exception(msg)
        process = None
        try:
            process = subprocess.Popen(args,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       bufsize=1,
                                       **kwargs
                                       )
            with self._router.capture_logs(
                cell_id,
                stdout=process.stdout,
                stderr=process.stderr
            ):
                self._cell_status_map[cell_id] = Value('i', process.pid)
                process.wait()
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
        self._start_listener()

    def submit(self, cell_id, *args, **kwargs):
        """Submit a new job for given cell id"""
        if not hasattr(self, '_listener'):
            raise RuntimeError('Instances of {} must be started via `start` '
                               'method before submit is called'.format(
                                   __class__.__name__))
        self._request_queue.put_nowait([cell_id, args, kwargs])

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
        self._request_queue.close()
