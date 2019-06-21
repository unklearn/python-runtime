# coding: utf8

from core.constants import CellEvents, CellExecutionStatus, CELLS_NAMESPACE

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class LocalSocketIO:
    """A route specific socketio object.

    Usually when events are emitted, they must happen over a namespace and channel.
    This class wraps the global socketio object into request local emitter
    """

    def __init__(self, socketio, channel, namespace):
        self.socketio = socketio
        self.channel = channel
        self.namespace = namespace

    def emit(self, event, args):
        self.socketio.emit(event,
                           args,
                           room=self.channel,
                           namespace=self.namespace)


class CellEventsSocket:
    """A socket emitter that emits events specific to a notebook cell"""

    def __init__(self, socketio, cell_id):
        """
        Parameters
        -----------
        socketio: LocalSocketIO
            The local socket event emitter

        cell_id: str
            The id of the cell
        """
        self.socketio = socketio
        self.cell_id = cell_id

    def start(self):
        self.socketio.emit(CellEvents.START_RUN, {
            'id': self.cell_id,
            'status': CellExecutionStatus.BUSY
        })

    def stdout(self, lines):
        self.socketio.emit(CellEvents.RESULT, {
            'id': self.cell_id,
            'output': '\n'.join(lines)
        })

    def stderr(self, lines):
        self.socketio.emit(CellEvents.RESULT, {
            'id': self.cell_id,
            'error': '\n'.join(lines)
        })

    def done(self, rc):
        if rc != 0:
            status = CellExecutionStatus.ERROR
        else:
            status = CellExecutionStatus.DONE
        self.socketio.emit(CellEvents.END_RUN, {
            'id': self.cell_id,
            'status': status
        })
