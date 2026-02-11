
# A Namespace is a dict that manages a set of named objects.
# One accesses it with a name, and it always returns an object,
# creating a new one if necessary.

class Namespace (dict):

    def __init__ (self, constructor, frozen=False):
        dict.__init__(self)
        self._constructor = constructor
        self._frozen = frozen

    def freeze (self):
        self._frozen = True

    def __getitem__ (self, key):
        if key not in self:
            if self._frozen:
                raise Exception('Attempt to create a new symbol in a frozen Namespace')
            self[key] = self._constructor(key)
        return dict.__getitem__(self, key)


#--  Value  --------------------------------------------------------------------

def atom (x):
    assert isinstance(x, str), f'Argument must be a string: {x}'
    return Value([x])

def is_sorted (lst):
    for i in range(len(lst)-1):
        if lst[i] >= lst[i+1]:
            return False
    return True


class Value (object):
    
    top = None
    bottom = None

    # when doing import from values, atoms is a string
    # otherwise, the atoms need to be in sort order

    def __init__ (self, atoms):
        if isinstance(atoms, str):
            self.atoms = tuple([atoms])
        else:
            self.atoms = tuple(atoms)
            assert is_sorted(self.atoms)

    def __or__ (self, other):
        if self is self.top or other is self.top:
            return self.top
        elif self is self.bottom:
            return other
        elif other is self.bottom:
            return self
        else:
            atoms1 = self.atoms
            atoms2 = other.atoms
            union = []
            i = 0
            j = 0
            while i < len(atoms1) and j < len(atoms2):
                if atoms1[i] < atoms2[j]:
                    union.append(atoms1[i])
                    i += 1
                elif atoms1[i] > atoms2[j]:
                    union.append(atoms2[j])
                    j += 1
                else:
                    union.append(atoms1[i])
                    i += 1
                    j += 1
            # at most one will apply
            if i < len(atoms1): union.extend(atoms1[i:])
            if j < len(atoms2): union.extend(atoms2[j:])
            return Value(union)

    def __and__ (self, other):
        if self is self.bottom or other is self.bottom:
            return self.bottom
        elif self is self.top:
            return other
        elif other is self.top:
            return self
        else:
            atoms1 = self.atoms
            atoms2 = other.atoms
            inter = []
            i = 0
            j = 0
            while i < len(atoms1) and j < len(atoms2):
                if atoms1[i] < atoms2[j]:
                    i += 1
                elif atoms1[i] > atoms2[j]:
                    j += 1
                elif atoms1[i] == atoms2[j]:
                    inter.append(atoms1[i])
                    i += 1
                    j += 1
                else:
                    raise Exception(f'Non-comparable atoms: {atoms1[i]} {atoms2[j]}')
            if inter:
                return Value(inter)
            else:
                return self.bottom

    ##  String representation.

    def __repr__ (self):
        if self is self.top:
            return 'ANY'
        elif self is self.bottom:
            return 'NULL'
        else:
            return '|'.join(self.atoms)

    ##  Create a category, using this value as syncat

    def __getitem__ (self, arg):
        # Order matters - Value is a specialization of tuple
        if isinstance(arg, Value):
            return Category((self, arg))
        elif isinstance(arg, tuple):
            return Category((self,) + arg)
        else:
            raise Exception(f'Illegal argument to []: {type(arg)} {arg}')


class Category (tuple):

    def __repr__ (self):
        t = self[0]
        args = self[1:]
        return repr(t) + '[' + ', '.join(repr(arg) for arg in args) + ']'


class Variable (str):
    pass


#-------------------------------------------------------------------------------

ANY = Value.top = Value([])
NULL = Value.bottom = Value([])

atoms = Namespace(atom)
variables = Namespace(Variable)

from . import autosym
__path__ = ['autosym::']
