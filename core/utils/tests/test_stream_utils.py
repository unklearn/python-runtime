# coding: utf8
import pytest
import asyncio
import sys


from ..stream import NonBlockingStream

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class FakeProcess:
    async def wait(self):
        fut = asyncio.Future()
        fut.set_result(True)
        return fut

    def kill(self):
        return 0

    @property
    def stdout(self):
        return FakeAwaitableStream('stdout')

    @property
    def stderr(self):
        return FakeAwaitableStream('stderr')

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


class LogCollector:

    def __init__(self):
        self.out_data = []
        self.err_data = []

    def collect(self, data):
        if data['key'] == 'out':
            self.out_data += data['lines']
        elif data['key'] == 'err':
            self.err_data += data['lines']

@pytest.mark.unit
@pytest.mark.stream_utils
@pytest.mark.asyncio
async def test_non_blocking_stream_running_event_loop(mocker):
    stream = NonBlockingStream()

    mocked = mocker.patch.object(asyncio, 'ensure_future', autospec=True)
    stream.start(lambda x: None)
    mocked.assert_called_once()


@pytest.mark.unit
@pytest.mark.stream_utils
def test_non_blocking_stream_non_running_event_loop(mocker):

    loop = asyncio.get_event_loop()

    stream = NonBlockingStream()

    mocked = mocker.patch.object(loop, 'run_until_complete', autospec=True)
    stream.start(lambda x: None)
    mocked.assert_called_once()


@pytest.mark.utils
@pytest.mark.stream_utils
@pytest.mark.asyncio
async def test_non_blocking_stream_read(mocker):
    stream = NonBlockingStream()
    string_stream = FakeAwaitableStream('test')
    stub = mocker.stub(name='fake_callback')
    await stream.read(string_stream, stub)

    stub.assert_called_once_with(['test'])


@pytest.mark.utils
@pytest.mark.stream_utils
@pytest.mark.asyncio
async def test_non_blocking_stream_concurrency(mocker):
    stream = NonBlockingStream()

    mocked = mocker.patch.object(asyncio, 'create_subprocess_exec', autospec=True)

    mocked.return_value = asyncio.Future()
    mocked.return_value.set_result(FakeProcess())

    stub = mocker.stub(name='fake_callback')
    await stream.read_concurrent(stub, ['dummy command'])

    stub.assert_any_call({
        'key': 'err',
        'lines': ['stderr']
    })

    stub.assert_any_call({
        'key': 'out',
        'lines': ['stdout']
    })


@pytest.mark.utils
@pytest.mark.stream_utils
@pytest.mark.asyncio
async def test_non_blocking_stream_concurrency_with_async_bash_command(mocker):
    stream = NonBlockingStream()

    stub = mocker.stub(name='fake_callback')
    await stream.read_concurrent(stub, "bash", "-c", 'sleep 0.01 && echo "First" && sleep 0.01 && '
                                                   'echo "Second" && sleep 0.01 && lsf')

    stub.assert_any_call({
        'key': 'out',
        'lines': ['First\n']
    })

    stub.assert_any_call({
        'key': 'out',
        'lines': ['Second\n']
    })

    stub.assert_any_call({
        'key': 'err',
        'lines': ['bash: lsf: command not found\n']
    })


@pytest.mark.utils
@pytest.mark.stream_utils
@pytest.mark.asyncio
async def test_non_blocking_stream_concurrency_with_async_python_command(mocker):
    stream = NonBlockingStream()

    collector = LogCollector()

    await stream.read_concurrent(collector.collect, sys.executable, "-c", "import asyncio\nasync def wait(s):\n"
                                                             "\tawait asyncio.sleep(0.01)\n"
                                                             "\tprint(s)\n"
                                                             "\tif s == 'Second':\n"
                                                             "\t\traise Exception('Oh nooes')\n"
                                                             "async def main():\n"
                                                             "\tawait wait('First')\n"
                                                             "\tawait wait('Second')\n"
                                                             "\tawait wait('Third')\n"
                                                             "loop = asyncio.get_event_loop()\n"
                                                             "loop.run_until_complete(main())\n")

    assert 'First\n' in collector.out_data
    assert 'Second\n' in collector.out_data

    assert 'Exception: Oh nooes\n' in collector.err_data
    assert 'Third\n' not in collector.out_data


@pytest.mark.utils
@pytest.mark.stream_utils
@pytest.mark.asyncio
async def test_non_blocking_stream_formatters(mocker):
    stream = NonBlockingStream({
        'stdout': lambda x: 'stdout::{}'.format(x),
        'stderr': lambda x: 'stderr::{}'.format(x)
    })

    mocked = mocker.patch.object(asyncio, 'create_subprocess_exec', autospec=True)

    mocked.return_value = asyncio.Future()
    mocked.return_value.set_result(FakeProcess())

    stub = mocker.stub(name='fake_callback')
    await stream.read_concurrent(stub, ['dummy command'])

    stub.assert_any_call({
        'key': 'err',
        'lines': ['stderr::stderr']
    })

    stub.assert_any_call({
        'key': 'out',
        'lines': ['stdout::stdout']
    })

@pytest.mark.utils
@pytest.mark.stream_utils
@pytest.mark.asyncio
async def test_non_blocking_stream_concurrent_streams(mocker):

    command = ['/bin/sh', 'echo "Hello"']

    mocked = mocker.patch.object(asyncio, 'create_subprocess_exec', autospec=True)

    mocked.return_value = asyncio.Future()
    mocked.return_value.set_result(FakeProcess())

    stream = NonBlockingStream()
    await stream.read_concurrent(lambda x: None, *command)
    mocked.assert_called_once_with(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
