import time
import os
import shlex
import asyncio
import signal
import psutil
from asyncio.subprocess import PIPE
from psutil import NoSuchProcess

import os
import stat

_fd_types = (('REG', stat.S_ISREG), ('FIFO', stat.S_ISFIFO),
             ('DIR', stat.S_ISDIR), ('CHR', stat.S_ISCHR),
             ('BLK', stat.S_ISBLK), ('LNK', stat.S_ISLNK), ('SOCK',
                                                            stat.S_ISSOCK))


def fd_table_status():
    result = []
    for fd in range(100):
        try:
            s = os.fstat(fd)
        except:
            continue
        for fd_type, func in _fd_types:
            if func(s.st_mode):
                break
        else:
            fd_type = str(s.st_mode)
        result.append((fd, fd_type))
    return result


def fd_table_status_logify(fd_table_result):
    return ('Open file handles: ' +
            ', '.join(['{0}: {1}'.format(*i) for i in fd_table_result]))


def fd_table_status_str():
    return fd_table_status_logify(fd_table_status())


class AsyncProcess:
    """Non blocking async process for reading stderr and stdout streams in a non
     blocking fashion

    Based on: # https://stackoverflow.com/questions/17190221/
    subprocess-popen-cloning-stdout-and-stderr-both-to-terminal-and-
    variables/25960956#25960956
    """

    def __init__(self,
                 registry_object,
                 stdout_cb=None,
                 stderr_cb=None,
                 done_cb=None,
                 formatters=None):
        """"
        Parameters
        ----------
        registry_object: ProcessRegistyObject
            An object that holds the process registry information
            The process registry contains the mapping from notebook cell to
            process pid. When the process registers with the registry,
            it gets a callback. The callback will be used to relay process
            output

        stdout_cb: method
            A callback function to execute when stdout is received.
            Method will be called with [lines] from process stdout

        stderr_cb: method
            A callback function to execute when stderr is received
            Method will be called with [lines] from process stderr

        done_cb: method
            A callback function to execute when process is done.
            Method will be called with return code

        formatters: dict
            Dictonary of formatters for stdout and stderr.
            e.g {
                # Replace temporary shell filename references
                'stdout': lambda x: x.replace('.sh', '')
                }
        """
        self.registry_object = registry_object
        self.stdout = stdout_cb
        self.stderr = stderr_cb
        self.done = done_cb
        self.formatters = formatters or {}

    async def read(self, stream, display, formatter=None, logging_interval=0):
        """Read from stream line by line until EOF, capture lines and call
        display method.

        Parameters
        ----------
        stream: Stream
            The process stdout, stderr stream

        display: method
            The callback method to execute when output is triggered

        formatter: method, optional
            An optional formatter method that can be used for format stream output

        logging_interval: int, optional
            An optional logging interval. If provided, logs will be sent with
            the specified interval

        """
        if not formatter:
            formatter = lambda x: x

        # Record the current start time
        start = time.time()

        # Store the emitted lines in an array
        lines = []

        # Read and wait for next lien
        while True:
            print('Waiting for', stream)
            line = await stream.readline()
            # If no logging interval is defined, immediately callback
            if logging_interval == 0:
                # EOF or end of stream
                if not line:
                    break
                else:
                    # Decode using utf-8
                    display([formatter(line.decode('utf-8'))])
                    continue
            if not line:
                if len(lines):
                    display(lines)
                break
            time_elapsed = time.time() - start

            # Time elapsed > logging interval => Display
            if time_elapsed > logging_interval:
                display(lines)
                lines = []
                start = time.time()
            else:
                lines.append(formatter(line.decode('utf-8')))

    async def feed_stdin(self, stdin):
        """A public copy of asyncio.subprocess.Process._feed_stdin"""
        while True:
            cmd = input()
            # Write to stdin
            stdin.write(cmd)
            stdin.flush()
            #try:
            print('AWaiting drain')
            #await stdin.drain()
            # except (BrokenPipeError, ConnectionResetError) as exc:
            #     print(exc)
            #     # communicate() ignores BrokenPipeError and ConnectionResetError
            #     pass
            print('Done feeding')

    @staticmethod
    def kill_child_processes(process):
        # The process is asnycio.process. Using psutil we can get children
        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for p in children:
                p.send_signal(signal.SIGTERM)
        except NoSuchProcess:
            pass

    @staticmethod
    async def kill(process):
        AsyncProcess.kill_child_processes(process)
        process.kill()
        return await process.wait()

    async def run(self, cmd_with_args, input=None):
        """Capture cmd's stdout, stderr while displaying them as they arrive
        (line by line).

        Call this method if you are already inside an event loop. Otherwise call start

        cmd_with_args: list
            The command to execute with arguments

        input: str, optional
            The input into the command. If not present stdin is not enabled

        """
        # start process using Subprocess command
        r, w = os.pipe()
        self.r = r
        self.w = os.fdopen(w, 'w')
        # Listening on socket, send messages.
        # Keep track of status within object
        # if busy, add to internal queue
        process = await asyncio.create_subprocess_exec(
            *cmd_with_args + [str(r)],
            stdin=r,
            stdout=PIPE,
            stderr=PIPE,
            pass_fds=(r, w))
        #self.w.close()
        self.process = process
        #reader = os.fdopen(r, 'r')
        #os.close(r)
        print('Closing')
        # Register with registry so that server can interrupt process, send input etc
        self.registry_object.register(process)

        try:
            # Internal execution queue, that waits for process to finish
            # If execution queue is full, we apply backpressure and drop
            # new requests
            print('Gathering')
            await asyncio.gather(
                self.feed_stdin(self.w),
                self.read(process.stdout, self.stdout,
                          self.formatters.get('stdout', None)),
                self.read(process.stderr, self.stderr,
                          self.formatters.get('stderr', None)))
            print('After gathering')
        except Exception as e:
            print(e)
            AsyncProcess.kill_child_processes(process)
            process.kill()
            # Kill child process if any
            self.stderr([str(e)])
        finally:
            print('Finally')
            # wait for the process to exit
            # rc = await process.wait()
            # self.done(rc)
            # self.registry_object.deregister()

        # Send the return code back
        return 0

    def start(self, cmd_string, input=None):
        """Start the command and wait for output in a non blocking fashion.

        Parameters
        ----------
        cmd_string: str
            The command with arguments to the command as a string

        input: str, optional
            Optional input that will be fed into stdin
        """
        # run the event loop
        if os.name == 'nt':
            loop = asyncio.ProactorEventLoop(
            )  # for subprocess' pipes on Windows
            asyncio.set_event_loop(loop)
        else:
            loop = asyncio.get_event_loop()

        if loop.is_running():
            return asyncio.ensure_future(self.run(shlex.split(cmd_string),
                                                  input=input),
                                         loop=loop)
        else:
            return loop.run_until_complete(
                self.run(shlex.split(cmd_string), input=input))
