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


def secure_relative_file_path(file_path):
    """Return a secure version of file path by making path absolute

    Parameters
    ----------
    file_path: str
        The path to file

    Returns
    -------
    str
        The path with all relative references removed
    """
    file_path = file_path.replace('..', '')
    file_path = re.sub(r"{}+".format(os.sep), os.sep, file_path).lstrip(os.sep)
    return file_path.replace('~', '').lstrip(os.sep)
