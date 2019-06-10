import pytest
import os

from ..file_utils import create_temporary_shell_file, secure_relative_file_path


@pytest.mark.unit
@pytest.mark.utils
def test_temporary_shell_file_creation():
    with create_temporary_shell_file('cid', 'contents', '/tmp') as filename:
        assert os.path.exists(filename)
        with open(filename, 'r') as f:
            assert f.read() == 'contents'
        assert os.system('if [ -x {} ]; then true else false; fi'.format(filename)) == 0
        assert filename.endswith('.sh')
    assert not os.path.exists(filename)


@pytest.mark.unit
@pytest.mark.utils
def test_secure_absolute_path():
    assert secure_relative_file_path('../../../.ssh/config') == '.ssh/config'
    assert secure_relative_file_path('~/config') == 'config'
    assert secure_relative_file_path('../../~/config') == 'config'
