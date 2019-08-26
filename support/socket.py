# coding: utf8
import asyncio
import json
import requests

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class DummySocketIO:
    def __init__(self):
        self._queue = []

    def emit(self, event, args, **kwargs):
        # Print here for tests that fail. Useful for debugging.
        # If tests pass, stdout is suppressed
        print('DummySocketIO::log', 'event:', event, 'payload', args, kwargs)
        self._queue.append({'event': event, 'args': args, 'kwargs': kwargs})

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

    async def find_event_async(self, event, args, **kwargs):
        timeout_counter = 0
        # Use poll to await and throw if timeout is exceeded
        while True:
            ev = self.find_event(event, args, **kwargs)
            if not ev:
                timeout_counter += 1
                if timeout_counter >= 5:
                    return False
                else:
                    await asyncio.sleep(0.5)
            else:
                return True


class HttpSocketIO:
    """A class that pushes messages to a given http endpoint"""

    def __init__(self, srv_addr):
        self.url = srv_addr
        self.session = requests.Session()

    def emit(self, event, args, **kwargs):
        with self.session:
            requests.post(self.url + '/runtime-messages', json=args)
