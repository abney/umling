
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
        
    def __bool__ (self):
        return bool(self.elements)

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

    def __add__ (self, other):
        if isinstance(other, (Set, Language)):
            return NotImplemented
        else:
            return coerce(self, Language) + other

    def __mul__ (self, other):
        if isinstance(other, (Set, Language)):
            return NotImplemented
        else:
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
        
    def __bool__ (self):
        return bool(self.data)

    def __iter__ (self):
        return iter(self.data)


class EnumSet (Set):

    def __init__ (self, elts):
        self.data = coerce(elts, frozenset)

    def __hash__ (self):
        return hash(self.data)

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
        return coerce(self, Language) * coerce(other, Language)

#         if isinstance(other, (EnumSet, builtins.set, frozenset)):
#             return EnumSet(coerce(x, Sequence) * coerce(y, Sequence) for x in self for y in other)
#         elif isinstance(other, Sequence):
#             return EnumSet(coerce(x, Sequence) * other for x in self)
#         else:
#             return EnumSet(coerce(x, Sequence) * coerce(other, Sequence) for x in self)

    def __rmul__ (self, other):
        return coerce(other, Language) * coerce(self, Language)

    def __language__ (self):
        if not self.data:
            return EmptyLanguage()
        else:
            return Union(Concatenation(coerce(elt, Sequence)) for elt in self)


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



#--  Pyfoma  -------------------------------------------------------------------

def _sym_to_pyfoma (sym):
    if sym is other:
        return '.'
    elif sym == '.':
        return '<period>'
    elif sym is epsilon:
        return ''
    else:
        return sym

def _sym_from_pyfoma (sym):
    if sym == '.':
        return other
    elif sym == '<period>':
        return '.'
    elif not sym:
        return epsilon
    else:
        return sym

def _from_pyfoma (syms):
    return Sequence(_sym_from_pyfoma(sym) for sym in syms if sym)


#--  Regular expressions  ------------------------------------------------------

def _fst_transitions (fst):
    for q in fst.states:
        for (label, transitions) in q.transitions.items():
            for trans in transitions:
                if len(trans.label) == 1:
                    insym = trans.label[0]
                    label = repr(insym if insym else epsilon)
                else:
                    label = ':'.join(repr(sym if sym else epsilon) for sym in trans.label)
                yield (q.name, label, trans.targetstate.name)

def _copy_fst (fst):
    out = FST()
    out.states = builtins.set()
    statemap = {}
    for q in fst.states:
        outq = State(name=q.name)
        statemap[id(q)] = outq
        out.states.add(outq)
    out.initialstate = statemap[id(fst.initialstate)]
    for q in fst.states:
        outq = statemap[id(q)]
        for (lbl, trs) in q.transitions.items():
            for t in trs:
                outq2 = statemap[id(t.targetstate)]
                outq.add_transition(outq2, t.label, t.weight)
    out.finalstates = {statemap[id(q)] for q in fst.finalstates}
    out.alphabet = fst.alphabet.copy()
    return out


class Language (object):

    istransducer = None
    isfinite = None

    def __init__ (self):
        self._fst = None

    def fst (self):
        '''
        We must be careful - the FST operations are destructive! Any user that
        wants to call an operation on my fst should use __fst__(), not fst().
        '''
        if self._fst is None:
            self._fst = self.__fst__()
            assert isinstance(self._fst, FST), f'Bad return from __fst__(): {repr(self._fst)}'
        return self._fst

    def __fst__ (self):
        '''
        Create a NEW fst representing this language, to be owned by the caller.
        '''
        return NotImplemented

    def __eq__ (self, other):
        return NotImplemented

    def __bool__ (self):
        try:
            next(self.__iter__())
            return True
        except StopIteration:
            return False

    def __iter__ (self):
        return iter(FSA(self.fst(), self.istransducer))

    def to_fsa (self):
        return FSA(self.fst(), self.istransducer)

    def __contains__ (self, x):
        return self.to_fsa().__contains__(x)

    def __call__ (self, x):
        return self.to_fsa()(x)

    def inv (self, x):
        return self.to_fsa().inv(x)

    def __hash__ (self):
        return hash(self.data)

    def __add__ (self, other):
        other = coerce(other, Language)
        return Union([self, other])

    def __sub__ (self, other):
        other = coerce(other, Language)
        return Difference([self, other])

    def __mul__ (self, other):
        other = coerce(other, Language)
        return Concatenation([self, other])

    def __rmul__ (self, other):
        other = coerce(other, Language)
        return Concatenation([other, self])

    def __matmul__ (self, other):
        other = coerce(other, Language)
        return Composition([self, other])

    def __rmatmul__ (self, other):
        other = coerce(other, Language)
        return Composition([other, self])

    # not used
    def __set__ (self):
        if self.isfinite:
            return EnumSet(iter(self))
        else:
            return NotImplemented

    def __repr__ (self):
        s = self.__bare__()
        if s.startswith('(') and s.endswith(')'):
            s = s[1:-1]
        return '/' + s + '/'

    def _show_fst (self):
        fst = self.fst()
        print('Initial:', fst.initialstate.name)
        print('Final:', ' '.join(repr(q.name) for q in fst.finalstates))
        print('Edges:')
        for (q1, label, q2) in sorted(_fst_transitions(fst)):
            print(' ', q1, label, q2)

    def to_sequence (self):
        raise ValueError(f'Cannot be coerced to a sequence: {self}')

    def to_symbol (self):
        raise ValueError(f'Cannot be coerced to a symbol: {self}')


def lg (x):
    return coerce(x, Language)


class Enum (object):

    @staticmethod
    def seqlen (x):
        if isinstance(x, tuple) and len(x) > 0 and isinstance(x[0], (Sequence, tuple, list)):
            return sum(len(elt) for elt in x)
        else:
            return len(x)

    def __init__ (self, x, n=10):
        elts = []
        self.truncated = False
        for (i, elt) in enumerate(x):
            if i >= n:
                self.truncated = True
                break
            elts.append(elt)
        elts.sort(key=repr)
        elts.sort(key=self.seqlen)
        self.elts = elts

    def _words (self):
        for (i, elt) in enumerate(self.elts):
            yield(f'[{i}] {elt}')
        if self.truncated:
            yield '...'

    def __repr__ (self):
        s = '\n'.join(self._words())
        if s:
            return s
        else:
            return '(empty)'


def enum (x, n=10):
    return Enum(x, n)


class Atom (Language):

#    @staticmethod
#    def _visible (c):
#        tab = {' ': '\u2423', '\r': '\u240d', '\t': '\u2409', '\n': '\u2424'}
#        return tab[c] if c in tab else c

    def __init__ (self, x):
        Language.__init__(self)
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
        return Sequence([self.data])


class Atoms (object):

    def __getattr__ (self, name):
        return self.__call__(name)

    def __call__ (self, name):
        if name == 'epsilon':
            return Concatenation([])
        elif name == 'emptyset':
            return EmptyLanguage()
        else:
            return Atom(name)


class Other (Language):

    def __init__ (self, name):
        Language.__init__(self)
        self.data = name
        self.istransducer = False
        self.isfinite = True

    def __fst__ (self):
        return FST(label=('.',))

    def __bare__ (self):
        return self.data

    def __repr__ (self):
        return self.data

    def to_symbol (self):
        return self.data

    def to_sequence (self):
        return Sequence([self.data])


class EmptyLanguage (Language):

    def __init__ (self):
        Language.__init__(self)
        self.data = emptyset

    def __fst__ (self):
        return FST()

    def __bare__ (self):
        return '\u2205'


def sym (x):
    if isinstance(x, Atom):
        return x
    else:
        return Atom(x)


class Union (Language):

    def __init__ (self, args):
        Language.__init__(self)
        self.args = tuple(coerce(x, Language) for x in args)
        self.istransducer = any(arg.istransducer for arg in self.args)
        self.isfinite = all(arg.isfinite for arg in self.args)
        
    def __fst__ (self):
        fst = self.args[0].__fst__()
        for x in self.args[1:]:
            fst = fst.union(x.__fst__())
        return fst
        
    def __bare__ (self):
        if len(self.args) > 1:
            return '(' + ' + '.join(sorted(arg.__bare__() for arg in self.args)) + ')'
        elif len(self.args) == 1:
            return self.args[0].__bare__()
        else:
            return '\u2205'


class CharRange (Language):

    def __init__ (self, c1, c2):
        Language.__init__(self)
        i = ord(c1)
        j = ord(c2)+1
        if j <= i: (i, j) = (j, i)
        self.i = i
        self.j = j
        self.istranducer = False
        self.isfinite = True

    def __fst__ (self):
        fst = None
        for i in range(self.i, self.j):
            charfst = FST(label=(chr(i),))
            if fst is None:
                fst = charfst
            else:
                fst = fst.union(charfst)
        return fst

    def __bare__ (self):
        return f'[{chr(self.i)}-{chr(self.j-1)}]'


def crange (c1, c2):
    return CharRange(c1, c2)


class Difference (Language):

    def __init__ (self, args):
        Language.__init__(self)
        assert len(args) > 0, 'Difference requires arguments'
        self.args = tuple(coerce(x, Language) for x in args)
        self.istransducer = self.args[0].istransducer
        self.isfinite = self.args[0].isfinite
        
    def __fst__ (self):
        fst = self.args[0].__fst__()
        for x in self.args[1:]:
            fst = fst.difference(x.__fst__())
        return fst
        
    def __bare__ (self):
        if len(self.args) > 1:
            return '(' + ' - '.join(arg.__bare__() for arg in self.args) + ')'
        elif len(self.args) == 1:
            return self.args[0].__bare__()
        else:
            raise Exception('This cannot happen')


class Concatenation (Language):

    def __init__ (self, args):
        Language.__init__(self)
        self.args = tuple(coerce(x, Language) for x in args)
        self.istransducer = any(arg.istransducer for arg in self.args)
        self.isfinite = all(arg.isfinite for arg in self.args)

    def __fst__ (self):
        if len(self.args) == 0:
            return FST(label=('',))
        fst = self.args[0].__fst__()
        for x in self.args[1:]:
            fst = fst.concatenate(x.__fst__())
        return fst

    def __bare__ (self):
        if len(self.args) > 1:
            return '(' + '\u22C5'.join(arg.__bare__() for arg in self.args) + ')'
        elif len(self.args) == 1:
            return self.args[0].__bare__()
        else:
            return '\u03b5'

    def to_sequence (self):
        return Sequence(self._symbols())

    def _symbols (self):
        for arg in self.args:
            if isinstance(arg, Concatenation):
                yield from arg._symbols()
            else:
                yield arg.to_symbol()


class KleeneClosure (Language):

    def __init__ (self, arg):
        Language.__init__(self)
        self.arg = coerce(arg, Language)
        self.istransducer = self.arg.istransducer
        self.isfinite = False
        
    def __fst__ (self):
        return self.arg.__fst__().kleene_closure()
        
    def __bare__ (self):
        return self.arg.__bare__() + '*'


def star (x):
    return KleeneClosure(x)


class Optional (Language):

    def __init__ (self, arg):
        Language.__init__(self)
        self.arg = coerce(arg, Language)
        self.transducer = self.arg.istransducer
        self.isfinite = self.arg.isfinite

    def __fst__ (self):
        return self.arg.__fst__().optional()

    def __bare__ (self):
        return self.arg.__bare__() + '?'


def opt (x):
    return Optional(x)


class CrossProduct (Language):

    def __init__ (self, args):
        Language.__init__(self)
        self.args = tuple(coerce(x, Language) for x in args)
        self.istransducer = True
        self.isfinite = all(arg.isfinite for arg in self.args)

    def __fst__ (self):
        if len(self.args) != 2:
            raise Exception('Cross product (:) requires exactly two arguments')
        return self.args[0].__fst__().cross_product(self.args[1].__fst__())

    def __bare__ (self):
        return '(' + self.args[0].__bare__() + ':' + self.args[1].__bare__() + ')'


def io (x, y):
    return CrossProduct([x,y])


class Composition (Language):

    def __init__ (self, args):
        assert isinstance(args, (list, tuple)) and len(args) > 0, 'Composition requires at least one argument'
        Language.__init__(self)
        self.args = tuple(coerce(x, Language) for x in args)
        self.istransducer = any(arg.istransducer for arg in self.args)
        self.isfinite = all(arg.isfinite for arg in self.args)

    def __fst__ (self):
        fst = self.args[0].__fst__()
        for x in self.args[1:]:
            fst = fst.compose(x.__fst__())
        return fst

    def __bare__ (self):
        return '(' + '@'.join(arg.__bare__() for arg in self.args) + ')'


class RewriteRule (Language):

    def __init__ (self, args):
        Language.__init__(self)
        assert isinstance(args, (list, tuple)) and len(args) == 3, 'Rewrite rule requires exactly three arguments'
        (xy, left, right) = args
        xy = coerce(xy, Language)
        left = Concatenation([]) if left is None else coerce(left, Language)
        right = Concatenation([]) if right is None else coerce(right, Language)
        self.args = (xy, left, right)
        self.istransducer = True
        self.isfinite = False

    def __fst__ (self):
        (fst, left, right) = (arg.__fst__() for arg in self.args)
        return fst.rewrite((left, right))

    def __bare__ (self):
        return '(' + ' '.join(self.args[0].__bare__(), '/', self.args[1].__bare__(), '_', self.args[2].__bare__()) + ')'


def rewrite (x, y, after=None, before=None):
    return RewriteRule([io(x, y), after, before])


#--  FSABuilder  ---------------------------------------------------------------

class FSABuilder (object):

    def __init__ (self):
        self.fst = None
        self.istransducer = False

    def _require_fsa (self):
        if self.fst is None:
            self.fst = FST()
            self.fst.initialstate.name = 1
        return self.fst

    def _require_state (self, q):
        fst = self._require_fsa()
        for state in fst.states:
            if state.name == q:
                return state
        state = State(name=q)
        fst.states.add(state)
        return state

    def _get_transition (self, q1, label, q2):
        if label in q1.transitions:
            for trans in q1.transitions[label]:
                if trans.targetstate == q2:
                    return trans

    @staticmethod
    def _de_epsilon (sym):
        return '' if sym == epsilon else sym

    def E (self, *args):
        if len(args) == 2:
            (q1, q2) = args
            label = ('',)
        elif len(args) == 3:
            (q1, insym, q2) = args
            label = (self._de_epsilon(insym),)
        elif len(args) == 4:
            (q1, insym, outsym, q2) = args
            label = (self._de_epsilon(insym), self._de_epsilon(outsym))
            self.istransducer = True
        else:
            raise Exception('Too many arguments to E')

        q1 = self._require_state(q1)
        q2 = self._require_state(q2)
        if not self._get_transition(q1, label, q2):
            q1.add_transition(q2, label, 0.)
            for sym in label:
                self.fst.alphabet.add(sym)

    def F (self, q):
        q = self._require_state(q)
        if q not in self.fst.finalstates:
            q.finalweight = 0.
            self.fst.finalstates.add(q)

    def make_fsa (self):
        self._require_fsa() # create an empty one if none exists
        fsa = FSA(self.fst, self.istransducer)
        self.erase_fsa()
        return fsa

    def erase_fsa (self):
        self.fst = None
        self.istransducer = False

    def edit_fsa (self, fsa):
        assert isinstance(fsa, Language), f'Can only edit FSAs or languages: {fsa}'
        self.fst = fsa.__fst__()
        self.istransducer = fsa.istransducer


class FSA (Language):

    def __init__ (self, fst, istransducer):
        '''
        The FSA will not call any destructive operations on fst, so it is fine to pass in an FST that you own.
        '''
        if fst is None: raise Exception('No fst')
        Language.__init__(self)
        self._fst = fst
        self.istransducer = self.compute_istransducer() if istransducer is None else istransducer

    def __fst__ (self):
        return _copy_fst(self._fst)

    def compute_istransducer (self):
        return any(len(label) > 1 for label in self.labels())

    def _labels (self):
        for q in self._fst.states:
            for label in q.transitions:
                yield label

    def labels (self):
        return set(self._labels())

    def __iter__ (self):
        visited = builtins.set()
        for item in self._iter1():
            if item not in visited:
                yield item
                visited.add(item)

    def _iter1 (self):
        fst = self._fst
        if self.istransducer:
            for (cost, pairseq) in fst.words():
                insyms = []
                outsyms = []
                for pair in pairseq:
                    if len(pair) == 1:
                        if pair[0]:
                            insyms.append(pair[0])
                            outsyms.append(pair[0])
                    elif len(pair) == 2:
                        if pair[0]:
                            insyms.append(pair[0])
                        if pair[1]:
                            outsyms.append(pair[1])
                    else:
                        raise Exception(f'Unexpected pair: {pair}')
                yield (_from_pyfoma(insyms), _from_pyfoma(outsyms))
        else:
            for (cost, pairseq) in fst.words():
                yield _from_pyfoma(pair[0] for pair in pairseq)

    def _call (self, x, invert=False):
        x = coerce(x, Sequence)
        fst = self._fst
        fst.tokenize_against_alphabet = lambda x: x
        insyms = [_sym_to_pyfoma(sym) for sym in x]
        fnc = fst.analyze if invert else fst.generate
        return (_from_pyfoma(y) for y in fnc(insyms, tokenize_outputs=True))

    def __call__ (self, x, invert=False):
        return Enum(self._call(x, invert=invert))

    def inv (self, x):
        return self.__call__(x, invert=True)

    def __contains__ (self, x):
        try:
            next(self._call(x))
            return True
        except StopIteration:
            return False

    def __show__ (self):
        self._show_fst()

    def __graph__ (self):
        return self._fst.view()

    def __bare__ (self):
        a = 'T' if self.istransducer else 'A'
        return f'(FS{a} with {len(self._fst.states)} states)'

    def __repr__ (self):
        return self.__bare__()


def show (x):
    if hasattr(x, '__show__'):
        x.__show__()
    else:
        print(x)

def graph (x):
    if hasattr(x, '__graph__'):
        return x.__graph__()
    else:
        raise Exception('Not drawable')

#--  Coercion  -----------------------------------------------------------------

class CoercionError (ValueError): pass

class Coercion (object):

    coercions = {frozenset: [ ((builtins.set, list, tuple, types.GeneratorType), frozenset),
                              (object, lambda x: frozenset([x])) ],
                 Sequence: [ ((list, tuple, types.GeneratorType), Sequence),
                             (Language, lambda x: x.to_sequence()),
                             (object, lambda x: Sequence([x])) ],
                 EnumSet: [ ((list, tuple, types.GeneratorType), lambda x: EnumSet(iter(x))),
                            (object, EnumSet) ],
                 Atom: [ ((str, int, float, tuple), Atom) ],
                 Language: [ (str, Atom),
                          (Sequence, lambda x: Concatenation(x)),
                          (EnumSet, EnumSet.__language__) ]
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
epsilon = Sequence([])
emptyset = EnumSet([])
_fsa_builder = FSABuilder()
E = _fsa_builder.E
F = _fsa_builder.F
make_fsa = _fsa_builder.make_fsa
erase_fsa = _fsa_builder.erase_fsa
edit = _fsa_builder.edit_fsa
at = Atoms()
anysym = Other('anysym')
other = Other('other')
