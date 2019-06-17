import time
import os

import asyncio
from asyncio.subprocess import PIPE


class NonBlockingStream:
    """Non blocking async stream for reading stderr and stdout

    Based on: # https://stackoverflow.com/questions/17190221/
    subprocess-popen-cloning-stdout-and-stderr-both-to-terminal-and-variables/25960956#25960956
    """

    def __init__(self, formatters=None):
        """"
        Parameters
        ----------
        formatters: dict
            Dictonary of formatters for stdout and stderr.
            e.g {
                # Replace temporary shell filename references
                'stdout': lambda x: x.replace('.sh', '')
                }
        """
        self.formatters = formatters or {}

    async def read(self, stream,
                   display,
                   formatter=None,
                   logging_interval=0):
        """Read from stream line by line until EOF, capture lines and call display method.

        Parameters
        ----------
        stream: Stream
            The process stdout, stderr stream

        display: method
            The callback method to execute when output is triggered

        formatter: method, optional
            An optional formatter method that can be used for format stream output

        logging_interval: int, optional
            An optional logging interval. If provided, logs will be sent with the specified interval

        """
        if not formatter:
            formatter = lambda x: x

        # Record the current start time
        start = time.time()

        # Store the emitted lines in an array
        lines = []

        # Read and wait for next lien
        while True:
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

    def _get_keyed_callback(self, key, callback):
        """Generate a callback function that outputs stream with given key"""
        def get_keyed_cb(lines):
            return callback({
                'key': key,
                'lines': lines
            })
        return get_keyed_cb

    async def read_concurrent(self, callback, *cmd):
        """Capture cmd's stdout, stderr while displaying them as they arrive
        (line by line).

        """
        # start process using Subprocess command
        process = await asyncio.create_subprocess_exec(*cmd,
                                                       stdout=PIPE,
                                                       stderr=PIPE)

        try:
            await asyncio.gather(
                self.read(process.stdout, self._get_keyed_callback('out', callback), self.formatters.get('stdout', None)),
                self.read(process.stderr, self._get_keyed_callback('err', callback), self.formatters.get('stderr', None))
            )
        except Exception as e:
            process.kill()
            callback({
                'key': 'err',
                'lines': [str(e)]
            })
        finally:
            # wait for the process to exit
            rc = await process.wait()

        # Send the return code back
        return rc

    def start(self, callback, *command):
        """Start the command and wait for output in a non blocking fashion.

        Parameters
        ----------
        callback: method
            A callback function that will be called with output and logs from executing
            command
        """
        # run the event loop
        if os.name == 'nt':
            loop = asyncio.ProactorEventLoop()  # for subprocess' pipes on Windows
            asyncio.set_event_loop(loop)
        else:
            loop = asyncio.get_event_loop()

        if loop.is_running():
            asyncio.ensure_future(self.read_concurrent(callback, *command), loop=loop)
        else:
            loop.run_until_complete(
                self.read_concurrent(callback, *command))
