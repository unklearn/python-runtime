import json

from .base import BaseConfig


class DummySocketIO:

    def __init__(self):
        self._queue = []

    def emit(self, event, args, **kwargs):
        self._queue.append({
            'event': event,
            'args': args,
            'kwargs': kwargs
        })

    def has_event(self, event):
        return any([d['event'] == event for d in self._queue])

    def find_event(self, event, args, **kwargs):
        for d in self._queue:
            if json.dumps(d) == json.dumps({
                'event': event,
                'args': args,
                'kwargs': kwargs
            }):
                return True
        return False


class TestingConfig(BaseConfig):
    """Config for testing"""
    SERVER_URI = 'http://localhost:8763'
    REDIS_BROKER_URL = 'redis://redis:6379'

    SOCKETIO = DummySocketIO()