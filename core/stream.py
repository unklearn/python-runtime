import time
import os

import asyncio
from asyncio.subprocess import PIPE

from core.constants import CellExecutionStatus, CellEvents, CELLS_NAMESPACE


# https://stackoverflow.com/questions/17190221/subprocess-popen-cloning-stdout-and-stderr-both-to-terminal-and-variables/25960956#25960956
async def read_stream_and_display(stream,
                                  display,
                                  stream_type,
                                  logging_interval=1):
    """Read from stream line by line until EOF, capture lines and call display method."""
    # Emit logs every x seconds
    start = time.time()
    lines = []
    while True:
        line = await stream.readline()
        if logging_interval == 0:
            if not line:
                break
            else:
                display([line.decode('utf-8')], stream_type)
                continue
        if not line:
            if len(lines):
                display(lines, stream_type)
            break
        time_elapsed = time.time() - start
        if time_elapsed > logging_interval:
            # Stream to socket using variable
            display(lines, stream_type)
            lines = []
            start = time.time()
        else:
            lines.append(line.decode('utf-8'))
    return True


async def read_and_display(socketio, payload, filename, *cmd):
    """Capture cmd's stdout, stderr while displaying them as they arrive
    (line by line).

    """
    channel = payload['channel']
    cell_id = payload['cellId']

    # Start by signalling cell status
    socketio.emit(CellEvents.START_RUN, {
        'id': cell_id,
        'status': CellExecutionStatus.BUSY
    },
                  room=channel,
                  namespace=CELLS_NAMESPACE)

    # start process
    process = await asyncio.create_subprocess_exec(*cmd,
                                                   stdout=PIPE,
                                                   stderr=PIPE)

    def post_line_to_server(lines, stream_type):
        socketio.emit(CellEvents.RESULT, {
            'id':
            cell_id,
            'output':
            ''.join(lines).replace(filename, 'sh')
            if stream_type == 'stdout' else '',
            'error':
            ''.join(lines).replace(filename, 'sh')
            if stream_type == 'stderr' else '',
        },
                      room=channel,
                      namespace=CELLS_NAMESPACE)

    # read child's stdout/stderr concurrently (capture and display)

    # Emit via broker
    status = CellExecutionStatus.DONE
    try:
        await asyncio.gather(
            read_stream_and_display(process.stdout, post_line_to_server,
                                    'stdout', 0),
            read_stream_and_display(process.stderr, post_line_to_server,
                                    'stderr', 0))
    except Exception as e:
        process.kill()
        post_line_to_server([str(e)], 'stderr')
        status = CellExecutionStatus.ERROR
    finally:
        # wait for the process to exit
        rc = await process.wait()

        socketio.emit(CellEvents.END_RUN, {'id': cell_id, 'status': status})
    return rc


def capture_logs(socketio, payload, filename, *cmd):
    # run the event loop
    if os.name == 'nt':
        loop = asyncio.ProactorEventLoop()  # for subprocess' pipes on Windows
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    if loop.is_running():
        # Tornado runs a default event loop
        # This is python 3.5.1 !!
        asyncio.run_coroutine_threadsafe(
            read_and_display(socketio, payload, filename, *cmd), loop)
    else:
        loop.run_until_complete(
            read_and_display(socketio, payload, filename, *cmd))
