# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.
"""
PySnooper - Never use print for debugging again

Usage:

    import pysnooper

    @pysnooper.snoop()
    def your_function(x):
        ...

A log will be written to stderr showing the lines executed and variables
changed in the decorated function.

For more information, see https://github.com/cool-RR/PySnooper
"""

from .tracer import Tracer as snoop
from .variables import Attrs, Exploding, Indices, Keys


__version__ = '0.4.0'

