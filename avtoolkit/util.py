"""
avtoolkit.util

Utilities for the AV Toolkit.
"""

import tempfile
import shutil
from functools import wraps


def tempdir(func):
    """
    Create a temp directory, pass its path into the function and remove it afterwards.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        """ Function wrapper. """
        if "tmpdir" in kwargs:
            return func(*args, **kwargs)
        tmpdir = tempfile.mkdtemp()
        kwargs["tmpdir"] = tmpdir
        try:
            return func(*args, **kwargs)
        finally:
            shutil.rmtree(tmpdir)
    return wrapper
