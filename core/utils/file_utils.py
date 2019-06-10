import os
import re
from contextlib import contextmanager


@contextmanager
def create_temporary_shell_file(cell_id, contents, temp_dir='tmp'):
    """Create a temporary shell file in the runtime to execute bash scripts

    Parameters
    ----------
    cell_id: str
        The id of the cell

    contents: str
        The content of the file

    temp_dir: str
        The temporary file directory
    """
    # Create the filename
    filename = '/{}/.file_{}.sh'.format(temp_dir, cell_id)

    # Write contents to file
    with open(filename, 'w') as f:
        f.write(contents)

    # Make file executable
    os.system('chmod +x {}'.format(filename))

    # Yield using contextmanager
    try:
        yield filename
    finally:
        os.unlink(filename)


def secure_absolute_file_path(file_path, root_dir):
    """Given a file path and root directory, make sure that the path is relative to the root directory.

    This means that the path cannot go outside root directory

    Parameters
    ----------
    file_path: str
        The path to file

    root_dir: str
        The root directory for file path

    Returns
    -------
    str
        The path with root_dir as root directory and relative paths removed
    """
    file_path = file_path.replace('..', '')
    file_path = re.sub(r"{}+".format(os.sep), os.sep, file_path).lstrip(os.sep)
    return os.path.abspath(os.path.join(root_dir, file_path.replace('~', '').lstrip(os.sep)))
