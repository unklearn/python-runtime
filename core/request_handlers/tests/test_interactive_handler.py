import pytest
import json

import tornado.testing
from support.base_test_handler import TestHandlerBase

from core.constants import CellEvents, CellExecutionStatus, CELLS_NAMESPACE


@pytest.mark.handlers
@pytest.mark.integration
class TestInteractiveRequestHandler(TestHandlerBase):
    @tornado.testing.gen_test
    def test_interactive_shell_run(self):
        resp = yield self.http_client.fetch(
            self.get_url('/interactive?language=shell'),
            method='POST',
            body=json.dumps({
                'cellId': 'shcid',
                'channel': 'channel',
                'code': 'echo Hello'
            }),
            follow_redirects=False)

        assert resp.code == 200

        r = yield self.socketio.find_event_async(
            CellEvents.START_RUN, {
                'id': 'shcid',
                'status': CellExecutionStatus.BUSY
            },
            room='channel',
            namespace=CELLS_NAMESPACE)

        assert r is True

        r = yield self.socketio.find_event_async(CellEvents.RESULT, {
            'id': 'shcid',
            'output': 'Hello\n'
        },
                                                 room='channel',
                                                 namespace=CELLS_NAMESPACE)

        assert r is True

        r = yield self.socketio.find_event_async(
            CellEvents.END_RUN, {
                'id': 'shcid',
                'status': CellExecutionStatus.DONE
            },
            room='channel',
            namespace=CELLS_NAMESPACE)

        assert r is True

    @tornado.testing.gen_test
    def test_interactive_shell_run_error(self):
        resp = yield self.http_client.fetch(
            self.get_url('/interactive?language=shell'),
            method='POST',
            body=json.dumps({
                'cellId': 'shcid',
                'channel': 'channel',
                'code': 'lsx'
            }),
            follow_redirects=False)

        assert resp.code == 200
        r = yield self.socketio.find_event_async(
            CellEvents.START_RUN, {
                'id': 'shcid',
                'status': CellExecutionStatus.BUSY
            },
            room='channel',
            namespace=CELLS_NAMESPACE)

        assert r is True

        r = yield self.socketio.find_event_async(
            CellEvents.RESULT, {
                'id': 'shcid',
                'error': '/bin/bash: line 1: lsx: command not found\n'
            },
            room='channel',
            namespace=CELLS_NAMESPACE)

        assert r is True

        r = yield self.socketio.find_event_async(
            CellEvents.END_RUN, {
                'id': 'shcid',
                'status': CellExecutionStatus.ERROR
            },
            room='channel',
            namespace=CELLS_NAMESPACE)
        assert r is True

    def test_interactive_cell_run(self):
        resp = self.fetch('/interactive?language=python',
                          method='POST',
                          body=json.dumps({
                              'cellId': 'cellId',
                              'channel': 'channel',
                              'code': 'print("Hello")'
                          }),
                          follow_redirects=False)

        assert resp.code == 200
        assert self.socketio.find_event(CellEvents.START_RUN, {
            'id': 'cellId',
            'status': CellExecutionStatus.BUSY
        },
                                        room='channel',
                                        namespace=CELLS_NAMESPACE)
        assert self.socketio.find_event(CellEvents.RESULT, {
            'id': 'cellId',
            'output': 'Hello\n'
        },
                                        room='channel',
                                        namespace=CELLS_NAMESPACE)
        assert self.socketio.find_event(CellEvents.END_RUN, {
            'id': 'cellId',
            'status': CellExecutionStatus.DONE
        },
                                        room='channel',
                                        namespace=CELLS_NAMESPACE)

    def test_interactive_cell_run_error(self):
        resp = self.fetch('/interactive?language=python',
                          method='POST',
                          body=json.dumps({
                              'cellId': 'cellId',
                              'channel': 'channel',
                              'code': 'print('
                          }),
                          follow_redirects=False)

        assert resp.code == 200
        assert self.socketio.find_event(CellEvents.START_RUN, {
            'id': 'cellId',
            'status': CellExecutionStatus.BUSY
        },
                                        room='channel',
                                        namespace=CELLS_NAMESPACE)
        assert self.socketio.find_event(CellEvents.RESULT, {
            'id':
            'cellId',
            'error':
            '  File \"<string>\", line 1\n    print(\n         ^\nSyntaxError: unexpected EOF while parsing\n'
        },
                                        room='channel',
                                        namespace=CELLS_NAMESPACE)
        assert self.socketio.find_event(CellEvents.END_RUN, {
            'id': 'cellId',
            'status': CellExecutionStatus.ERROR
        },
                                        room='channel',
                                        namespace=CELLS_NAMESPACE)
