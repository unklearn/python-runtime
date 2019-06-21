# coding: utf8
import asyncio

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class FakeProcess:
    def __init__(self):
        self.stdin = FakeStdin()
        self.stdout = FakeAwaitableStream('stdout')
        self.stderr = FakeAwaitableStream('stderr')

    async def wait(self):
        fut = asyncio.Future()
        fut.set_result(0)
        return await fut

    def kill(self):
        return 0


class FakeAwaitableStream:
    def __init__(self, arg):
        self.arg = arg
        self.finished = False

    async def readline(self):
        if not self.finished:
            fut = asyncio.Future()
            fut.set_result(self.arg.encode('utf-8'))
            self.finished = True
            return await fut


class FakeStdin:
    def __init__(self):
        self.data = None

    def write(self, data):
        self.data = data

    async def drain(self):
        fut = asyncio.Future()
        fut.set_result(0)
        return await fut

    def close(self):
        return 0


class FakeRegistry:
    def register(self, p):
        self.p = p

    def deregister(self):
        pass

    def get_process(self):
        return self.p


class LogCollector:
    def __init__(self):
        self.out_data = []
        self.err_data = []

    def collect(self, data):
        if data['key'] == 'out':
            self.out_data += data['lines']
        elif data['key'] == 'err':
            self.err_data += data['lines']
