
from .lang import *

# This causes atoms and variables to be treated as sub-modules
from . import autosym
__path__ = ['autosym::']
