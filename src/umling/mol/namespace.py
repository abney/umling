
# A Namespace is a dict that manages a set of named objects.
# One accesses it with a name, and it always returns an object,
# creating a new one if necessary.
#
# ns(s) is equivalent to ns[s]
#

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

    def __call__ (self, key):
        return self.__getitem__(key)
