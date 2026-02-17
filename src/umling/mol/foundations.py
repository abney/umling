

class Concatenable:

    def __mul__ (self, other):
        return self.to_concatenable() * other

    def __rmul__ (self, other):
        return other * self.to_concatenable()


class Unionable:

    def __add__ (self, other):
        return self.to_unionable() * other

    def __radd__ (self, other):
        return other * self.to_unionable()


class Symbol (Concatenable, Unionable):

    to_concatenable = None  # set in lang.py
    to_unionable = None     # set in features.py

    def __init__ (self, x):
        self.data = x

    def __fst__ (self):
        return FST(label=(_sym_to_pyfoma(self.data),))

    def __bare__ (self):
        if isinstance(self.data, str):
            if not all(c.isalpha() for c in self.data):
                return repr(self.data)
            else:
                return self.data
        else:
            return repr(self.data)

    def to_symbol (self):
        return self.data

    def to_sequence (self):
        return tuple([self.data])

    def __getitem__ (self, *ftrs):
        return Category([self.data, *ftrs])

    def __repr__ (self):
        return self.__bare__()


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


symbols = Namespace(Symbol)
