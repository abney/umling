
from .lang import *
from .grammar import *

# This causes symbols and variables to be treated as sub-modules
from . import autosym
__path__ = ['autosym::']
