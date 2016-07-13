"""
avtoolkit.util

Utilities for the AV Toolkit.
"""

import tempfile
import shutil
import os
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


def chainable(func):
    """
    If no output_path is specified, generate an intermediate file and pass it to the function.
    Add the path of the intermediate file to the resulting Video.intermediate_files list before
    returning it. If an output_path is specified, use it and then delete the intermediate files.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        """ Function wrapper. """
        intermediate_required = "output_path" not in kwargs
        self = args[0]
        if intermediate_required:
            _, output_path = tempfile.mkstemp(
                dir=self.dirname, prefix=func.__name__, suffix=self.ext)
            kwargs["output_path"] = output_path
        try:
            ret = func(*args, **kwargs)
        except:
            if intermediate_required:
                os.unlink(output_path)
            raise
        finally:
            if self.intermediate_file is not None:
                os.unlink(self.intermediate_file)
            if intermediate_required:
                ret.intermediate_file = output_path
        return ret
    return wrapper
