import tempfile
import shutil


def tempdir(func):
    """
    Create a temp directory, pass its path into the function and remove it afterwards.
    """
    def wrapper(*args, **kwargs):
        tmpdir = tempfile.mkdtemp()
        try:
            func(tmpdir, *args, **kwargs)
        finally:
            shutil.rmtree(tmpdir)
    return wrapper
