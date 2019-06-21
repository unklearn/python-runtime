# coding: utf8
import pytest

from support.socket import DummySocketIO

from core.constants import CellEvents, CellExecutionStatus
from ..socket import LocalSocketIO, CellEventsSocket

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


@pytest.mark.unit
@pytest.mark.utils
def test_local_socketio(mocker):

    gsio = DummySocketIO()
    mocked = mocker.patch.object(gsio, 'emit', autospec=True)

    sio = LocalSocketIO(gsio, 'channel', 'namespace')

    sio.emit('test_event', 'test_args')

    assert mocked.call_count == 1

    mocked.assert_called_once_with('test_event',
                                   'test_args',
                                   room='channel',
                                   namespace='namespace')


@pytest.mark.unit
@pytest.mark.utils
def test_cell_events_socket_start(mocker):
    lio = LocalSocketIO(DummySocketIO(), 'c', 'n')

    csocket = CellEventsSocket(lio, 'cid')

    mocked = mocker.patch.object(lio, 'emit', autospec=True)

    csocket.start()

    assert mocked.call_count == 1
    mocked.assert_called_once_with(CellEvents.START_RUN, {
        'id': 'cid',
        'status': CellExecutionStatus.BUSY
    })


@pytest.mark.unit
@pytest.mark.utils
def test_cell_events_socket_stdout(mocker):
    lio = LocalSocketIO(DummySocketIO(), 'c', 'n')

    csocket = CellEventsSocket(lio, 'cid')

    mocked = mocker.patch.object(lio, 'emit', autospec=True)

    csocket.stdout(['a', 'b'])

    assert mocked.call_count == 1
    mocked.assert_called_once_with(CellEvents.RESULT, {
        'id': 'cid',
        'output': 'a\nb'
    })


@pytest.mark.unit
@pytest.mark.utils
def test_cell_events_socket_stderr(mocker):
    lio = LocalSocketIO(DummySocketIO(), 'c', 'n')

    csocket = CellEventsSocket(lio, 'cid')

    mocked = mocker.patch.object(lio, 'emit', autospec=True)

    csocket.stderr(['a', 'b'])

    assert mocked.call_count == 1
    mocked.assert_called_once_with(CellEvents.RESULT, {
        'id': 'cid',
        'error': 'a\nb'
    })


@pytest.mark.unit
@pytest.mark.utils
def test_cell_events_socket_done_success(mocker):
    lio = LocalSocketIO(DummySocketIO(), 'c', 'n')

    csocket = CellEventsSocket(lio, 'cid')

    mocked = mocker.patch.object(lio, 'emit', autospec=True)

    csocket.done(0)

    assert mocked.call_count == 1
    mocked.assert_called_once_with(CellEvents.END_RUN, {
        'id': 'cid',
        'status': CellExecutionStatus.DONE
    })


@pytest.mark.unit
@pytest.mark.utils
def test_cell_events_socket_done_error(mocker):
    lio = LocalSocketIO(DummySocketIO(), 'c', 'n')

    csocket = CellEventsSocket(lio, 'cid')

    mocked = mocker.patch.object(lio, 'emit', autospec=True)

    csocket.done(1)

    assert mocked.call_count == 1
    mocked.assert_called_once_with(CellEvents.END_RUN, {
        'id': 'cid',
        'status': CellExecutionStatus.ERROR
    })
