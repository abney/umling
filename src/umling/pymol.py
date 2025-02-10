
import builtins, types
from pyfoma import FST, State


#--  Sequence  -----------------------------------------------------------------

class Sequence (object):

    def __init__ (self, elts):
        self.elements = tuple(elts)

    def __iter__ (self):
        return iter(self.elements)

    def __fst__ (self):
        pass
        
    def __getitem__ (self, i):
        return self.elements[i]

    def __len__ (self):
        return len(self.elements)

    def __hash__ (self):
        return hash(self.elements)

    def __eq__ (self, other):
        return isinstance(other, Sequence) and self.elements == other.elements

    def __lt__ (self, other):
        assert isinstance(other, Sequence), 'Cannot compare sequence to non-sequence'
        return self.elements < other.elements

    def __mul__ (self, other):
        other = coerce(other, Sequence)
        return Sequence(self.elements + other.elements)
        
    def __rmul__ (self, other):
        other = coerce(other, Sequence)
        return Sequence(other.elements + self.elements)

    def __pow__ (self, n):
        assert isinstance(n, int), 'Power must be a number'
        return Sequence(tuple(self) * n)

    def __repr__ (self):
        if not self:
            return '\u03b5'
        else:
            return '<' + ', '.join(repr(x) for x in self) + '>'

epsilon = Sequence([])

def seq (*elts):
    if len(elts) == 1 and isinstance(elts[0], types.GeneratorType):
        return Sequence(elts[0])
    return Sequence(elts)

# def string (*elts):
#     return Sequence(coerce(x, Symbol) for x in elts)

def words (s):
    assert isinstance(s, str), 'Input must be a quoted string'
    return Sequence(s.split())

def letters (s):
    assert isinstance(s, str), 'Input must be a quoted string'
    return Sequence(s)


#--  Set  ----------------------------------------------------------------------

class Set (object):
 
    def __len__ (self):
        return len(self.data)

    def __hash__ (self):
        return hash(self.data)
        
    def __iter__ (self):
        return iter(self.data)


class EnumSet (Set):

    def __init__ (self, elts):
        self.data = coerce(elts, frozenset)

    def __eq__ (self, other):
        try:
            other = coerce(other, EnumSet)
            return self.data == other.data
        except CoercionError:
            return NotImplemented

    def __le__ (self, other):
        try:
            other = coerce(other, EnumSet)
            return self.data <= other.data
        except CoercionError:
            return NotImplemented

    def __or__ (self, other):
        try:
            other = coerce(other, EnumSet)
            return EnumSet(self.data | other.data)
        except CoercionError:
            return NotImplemented

    def __add__ (self, other):
        return self.__or__(other)

    def __and__ (self, other):
        try:
            other = coerce(other, EnumSet)
            return EnumSet(self.data & other.data)
        except CoercionError:
            return NotImplemented

    def __sub__ (self, other):
        try:
            other = coerce(other, EnumSet)
            return EnumSet(self.data - other.data)
        except CoercionError:
            return NotImplemented

    def __repr__ (self):
        if not self.data:
            return '\u2205'
        else:
            return '{' + ', '.join(sorted(repr(x) for x in self)) + '}'

    def __mul__ (self, other):
        if isinstance(other, (EnumSet, builtins.set, frozenset)):
            return EnumSet(coerce(x, Sequence) * coerce(y, Sequence) for x in self for y in other)
        elif isinstance(other, Sequence):
            return EnumSet(coerce(x, Sequence) * other for x in self)
        else:
            return EnumSet(coerce(x, Sequence) * coerce(other, Sequence) for x in self)


def set (*elts):
    if len(elts) == 1 and isinstance(elts[0], types.GeneratorType):
        return EnumSet(elts[0])
    else:
        return EnumSet(elts)

def vocab (*words):
    if len(words) == 1:
        if isinstance(words[0], types.GeneratorType):
            words = list(words[0])
        elif isinstance(words[0], (Sequence, tuple, list, EnumSet)):
            words = words[0]
        elif isinstance(words[0], str):
            words = words[0].split()
        else:
            raise Exception(f'Expecting words, got {words[0]}')
    assert all(isinstance(word, str) for word in words), 'Vocabulary elements must be quoted'
    assert all(' ' not in word for word in words), 'Vocabulary elements cannot contain spaces'
    return EnumSet(word for word in words)

def alphabet (*letters):
    if len(letters) == 1:
        if isinstance(letters[0], types.GeneratorType):
            letters = list(letters[0])
        else:
            letters = letters[0]
    assert all(isinstance(letter, str) for letter in letters), 'Alphabet elements must be quoted'
    assert all(len(letter) == 1 for letter in letters), 'Alphabet elements must be single letters'
    return EnumSet(letter for letter in letters)


#--  Regular expressions  ------------------------------------------------------

class Regex (object):

    fst = None
    istransducer = False
    isinfinite = False

    def __iter__ (self):
        visited = builtins.set()
        for item in self._iter1():
            if item not in visited:
                yield item
                visited.add(item)

    def _iter1 (self):
        if self.istransducer:
            for (cost, pairseq) in self.fst.words():
                insyms = []
                outsyms = []
                for pair in pairseq:
                    if len(pair) == 1:
                        insyms.append(pair[0])
                        outsyms.append(pair[0])
                    elif len(pair) == 2:
                        insyms.append(pair[0])
                        outsyms.append(pair[1])
                    else:
                        raise Exception(f'Unexpected pair: {pair}')
                yield (Sequence(insyms), Sequence(outsyms))
        else:
            for (cost, pairseq) in self.fst.words():
                yield Sequence(pair[0] for pair in pairseq)

    def __add__ (self, other):
        other = coerce(other, Regex)
        return Union([self, other])

    def __mul__ (self, other):
        other = coerce(other, Regex)
        return Concatenation([self, other])

    def lang (self):
        if self.isinfinite:
            return NotImplemented
        else:
            return EnumSet(iter(self))

    def __repr__ (self):
        s = self.__bare__()
        if s.startswith('(') and s.endswith(')'):
            s = s[1:-1]
        return '/' + s + '/'


def re (x):
    return coerce(x, Regex)


def lang (x):
    assert isinstance(x, Regex), f'Cannot coerce to language: {x}'
    return x.lang()

def enum (x, n=10):
    for (i, item) in enumerate(x):
        if i >= n:
            print('...')
            break
        print(f'[{i}]', item)


class Atom (Regex):

    @staticmethod
    def _visible (c):
        tab = {' ': '\u2423', '\r': '\u240d', '\t': '\u2409', '\n': '\u2424'}
        return tab[c] if c in tab else c

    def __init__ (self, x):
        self.data = x
        self.fst = FST(label=(x,))

    def __hash__ (self):
        return hash(self.data)

    def __eq__ (self, other):
        other = coerce(other, Atom)
        return self.data == other.data

    def __bare__ (self):
        if isinstance(self.data, str):
            if any(c.isspace() for c in self.data):
                return ''.join(self._visible(c) for c in self.data)
            else:
                return self.data
        else:
            return repr(self.data)

    def __repr__ (self):
        return '/' + self.__bare__() + '/'


def sym (x):
    if isinstance(x, Atom):
        return x
    else:
        return Atom(x)


class Union (Regex):

    def __init__ (self, args):
        self.args = tuple(coerce(x, Regex) for x in args)
        fst = self.args[0].fst
        for x in self.args[1:]:
            fst = fst.union(x.fst)
        self.fst = fst
        self.isinfinite = any(arg.isinfinite for arg in self.args)
        
    def __bare__ (self):
        if len(self.args) > 1:
            return '(' + ' + '.join(sorted(arg.__bare__() for arg in self.args)) + ')'
        elif len(self.args) == 1:
            return self.args[0].__bare__()
        else:
            return '\u2205'


class Concatenation (Regex):

    def __init__ (self, args):
        self.args = tuple(coerce(x, Regex) for x in args)
        if len(self.args) == 0:
            fst = FST(label=('',))
        else:
            fst = self.args[0].fst
        for x in self.args[1:]:
            fst = fst.concatenate(x.fst)
        self.fst = fst
        self.isinfinite = any(arg.isinfinite for arg in self.args)

    def __bare__ (self):
        if len(self.args) > 1:
            return '(' + '\u22C5'.join(arg.__bare__() for arg in self.args) + ')'
        elif len(self.args) == 1:
            return self.args[0].__bare__()
        else:
            return '\u03b5'


class KleeneClosure (Regex):

    def __init__ (self, arg):
        self.arg = coerce(arg, Regex)
        self.fst = self.arg.fst.kleene_closure()
        self.isinfinite = True
        
    def __bare__ (self):
        return self.arg.__bare__() + '*'


def star (x):
    return KleeneClosure(x)


#--  FSABuilder  ---------------------------------------------------------------

class FSABuilder (object):

    def __init__ (self):
        self.fsa = None

    def _require_fsa (self):
        if self.fsa is None:
            self.fsa = FST()
            self.fsa.initialstate.name = 0
        return self.fsa

    def _require_state (self, q):
        fsa = self._require_fsa()
        for state in fsa.states:
            if state.name == q:
                return state
        state = State(name=q)
        fsa.states.add(state)
        return state

    def _get_transition (self, q1, label, q2):
        for trans in q1.transitionsin[label[0]]:
            if trans.targetstate == q2 and trans.label == label:
                return trans

    def E (self, q1, label, q2, arg4=None):
        insym = label
        if insym == epsilon:
            insym = ''
        outsym = None
        if arg4 is None:
            label = (label,)
        if arg4 is not None:
            outsym = q2
            if outsym == epsilon:
                outsym = ''
            label = (insym, outsym)
            q2 = arg4
        q1 = self._require_state(q1)
        q2 = self._require_state(q2)
        if not self._get_transition(q1, label, q2):
            q1.add_transition(q2, label, 0.)
            for sym in label:
                self.fsa.alphabet.add(sym)

    def F (self, q):
        q = self._require_state(q)
        if q not in self.fsa.finalstates:
            q.finalweight = 0.
            self.fsa.finalstates.add(q)

    def make_fsa (self):
        self._require_fsa() # create an empty one if none exists
        fsa = self.fsa
        self.fsa = None
        return fsa

    def erase_fsa (self):
        self.fsa = None


#--  Coercion  -----------------------------------------------------------------

class CoercionError (ValueError): pass

class Coercion (object):

    coercions = {frozenset: [ ((builtins.set, list, tuple, types.GeneratorType), frozenset) ],
                 Sequence: [ ((list, tuple, types.GeneratorType), Sequence),
                             (object, lambda x: Sequence([x])) ],
                 EnumSet: [ (set, EnumSet),
                            ((list, tuple, types.GeneratorType), lambda x: EnumSet(iter(x))) ],
                 Atom: [ ((str, int, float, tuple), Atom) ],
                 Regex: [ (str, Atom),
                          (Sequence, lambda x: Concatenation(x)),
                          (EnumSet, lambda x: Union(Concatenation(coerce(elt, Sequence)) for elt in x)) ],
                 }                 

    def __call__ (self, x, typ):
        if isinstance(x, typ):
            return x
        for (tgts, f) in self.coercions.get(typ, []):
            if isinstance(x, tgts):
                v = f(x)
                if v is not NotImplemented:
                    return v
        raise CoercionError(f'Expecting a {typ}, but got {x}')


#--  Globals  ------------------------------------------------------------------

coerce = Coercion()
emptyset = EnumSet([])
_fsa_builder = FSABuilder()
E = _fsa_builder.E
F = _fsa_builder.F
make_fsa = _fsa_builder.make_fsa
erase_fsa = _fsa_builder.erase_fsa
