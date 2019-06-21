# coding: utf8
import pytest
import asyncio
import sys
from asyncio.subprocess import PIPE

from support.process import FakeProcess, FakeAwaitableStream, FakeRegistry, LogCollector
from ..process import AsyncProcess

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


@pytest.fixture(scope='function')
def dummy_async_process(mocker):
    r = FakeRegistry()
    stdout_stub = mocker.stub(name='fake_stdout_cb')
    stderr_stub = mocker.stub(name='fake_stderr_cb')
    done_stub = mocker.stub(name='fake_done_cb')
    return AsyncProcess(r,
                        stdout_cb=stdout_stub,
                        stderr_cb=stderr_stub,
                        done_cb=done_stub)


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.asyncio
async def test_async_process_running_event_loop(mocker):
    stream = AsyncProcess(None)

    mocker.patch.object(asyncio, 'ensure_future', autospec=True)
    stream.start('dummy command')
    assert asyncio.ensure_future.call_count == 1


@pytest.mark.unit
@pytest.mark.utils
def test_async_process_non_running_event_loop(mocker):

    loop = asyncio.get_event_loop()
    loop.stop()

    stream = AsyncProcess(None)

    mocked = mocker.patch.object(stream, 'run', autospec=True)
    f = asyncio.Future()
    f.set_result(1)
    mocked.return_value = f
    g = stream.start('Dummy')

    assert g == 1


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.asyncio
async def test_async_process_registration(mocker):

    r = FakeRegistry()
    fp = FakeProcess()
    fake_call = lambda x: 1
    register_mock = mocker.patch.object(r, 'register', autospec=True)
    deregister_mock = mocker.patch.object(r, 'deregister', autospec=True)
    stream = AsyncProcess(r,
                          stdout_cb=fake_call,
                          stderr_cb=fake_call,
                          done_cb=fake_call)

    mocked = mocker.patch.object(asyncio,
                                 'create_subprocess_exec',
                                 autospec=True)
    f = asyncio.Future()
    f.set_result(fp)
    mocked.return_value = f
    await stream.run('Dummy')

    r.register.assert_called_once_with(fp)
    r.deregister.assert_called_once()


@pytest.mark.utils
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_process_read(mocker):
    stream = AsyncProcess(None)
    string_stream = FakeAwaitableStream('test')
    stub = mocker.stub(name='fake_callback')
    await stream.read(string_stream, stub)

    stub.assert_called_once_with(['test'])


@pytest.mark.utils
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_process_concurrency(mocker, dummy_async_process):
    mocked = mocker.patch.object(asyncio,
                                 'create_subprocess_exec',
                                 autospec=True)

    mocked.return_value = asyncio.Future()
    mocked.return_value.set_result(FakeProcess())

    await dummy_async_process.run(['dummy command'])

    dummy_async_process.stdout.assert_any_call(['stdout'])

    dummy_async_process.stderr.assert_any_call(['stderr'])

    dummy_async_process.done.assert_any_call(0)


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.asyncio
async def test_async_process_stdin(mocker, dummy_async_process):
    mocked = mocker.patch.object(asyncio,
                                 'create_subprocess_exec',
                                 autospec=True)

    mocked.return_value = asyncio.Future()
    mocked.return_value.set_result(FakeProcess())

    await dummy_async_process.run(['bash'], 'dummy_input')

    asyncio.create_subprocess_exec.assert_called_once_with('bash',
                                                           stdin=PIPE,
                                                           stdout=PIPE,
                                                           stderr=PIPE)

    assert dummy_async_process.registry_object.get_process(
    ).stdin.data == b'dummy_input'


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.asyncio
async def test_async_process_concurrency_with_async_bash_command(
        dummy_async_process):
    await dummy_async_process.run([
        'bash'
    ], 'sleep 0.01 && echo First && sleep 0.01 && echo Second && sleep 0.01 && lsf'
                                  )

    dummy_async_process.stdout.assert_any_call(['First\n'])
    dummy_async_process.stdout.assert_any_call(['Second\n'])

    dummy_async_process.stderr.assert_any_call(
        ['bash: line 1: lsf: command not found\n'])
    dummy_async_process.done.assert_any_call(127)


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.asyncio
async def test_async_process_concurrency_with_async_python_command(
        dummy_async_process):
    await dummy_async_process.run([sys.executable],
                                  "import asyncio\nasync def wait(s):\n"
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

    dummy_async_process.stdout.assert_any_call(['First\n'])
    dummy_async_process.stdout.assert_any_call(['Second\n'])
    dummy_async_process.stderr.assert_any_call(['Exception: Oh nooes\n'])
    with pytest.raises(AssertionError):
        dummy_async_process.stdout.assert_any_call(['Third\n'])
    dummy_async_process.done.assert_any_call(1)


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.asyncio
async def test_async_process_formatters(mocker):
    stdout_stub = mocker.stub('fake_stdout_stub')
    stderr_stub = mocker.stub('fake_stderr_stub')
    stream = AsyncProcess(FakeRegistry(),
                          stdout_cb=stdout_stub,
                          stderr_cb=stderr_stub,
                          done_cb=lambda x: 1,
                          formatters={
                              'stdout': lambda x: 'stdout::{}'.format(x),
                              'stderr': lambda x: 'stderr::{}'.format(x)
                          })

    mocked = mocker.patch.object(asyncio,
                                 'create_subprocess_exec',
                                 autospec=True)

    mocked.return_value = asyncio.Future()
    mocked.return_value.set_result(FakeProcess())

    await stream.run(['dummy command'])

    stdout_stub.assert_any_call(['stdout::stdout'])
    stderr_stub.assert_any_call(['stderr::stderr'])
