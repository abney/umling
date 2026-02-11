
import sys
from importlib import import_module
from importlib.abc import MetaPathFinder, Loader
from importlib.util import spec_from_loader


class AutosymLoader (Loader):

    def __init__ (self, table):
        self.table = table

    def create_module (self, spec):
        return self.table

    def exec_module (self, table):
        pass


class AutosymFinder (MetaPathFinder):

    def find_spec (self, fullname, path, target=None):
        if path and 'autosym::' in path:
            i = fullname.rfind('.')
            if i >= 0:
                (parent_name, child_name) = (fullname[:i], fullname[i+1:])
                parent = import_module(parent_name)
                if child_name in parent.__dict__:
                    table = parent.__dict__[child_name]
                    return spec_from_loader(fullname, AutosymLoader(PseudoModule(fullname, table)))
        return None


class PseudoModule (object):

    def __init__ (self, name, symbol_table):
        assert isinstance(name, str)
        assert hasattr(symbol_table, '__getitem__')
        self.__name__ = name
        self.__package__ = None
        self.__loader__ = None
        self.__path__ = None
        self.__table__ = symbol_table

    def __getattr__ (self, name):
        return self.__table__[name]


sys.meta_path.append(AutosymFinder())
