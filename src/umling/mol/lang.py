
import builtins, types
from pyfoma import FST, State
from .namespace import Namespace

LANGLE = '\u27e8'
RANGLE = '\u27e9'
EPSILON = '\u03b5'
EMPTYSET = '\u2205'
CDOT = '\u2219'
RIGHTARROW = '\u2192'
SUPMINUS = '\u207b'
SUPONE = '\u00b9'


#--  Pyfoma  -------------------------------------------------------------------

def _to_input_tuple (x):
    if isinstance(x, tuple):
        return x
    elif isinstance(x, list):
        return tuple(x)
    elif isinstance(x, Language):
        return x.to_sequence()
    else:
        return tuple([x])

def _sym_to_pyfoma (sym):
    if sym is other:
        return '.'
    elif sym is epsilon:
        return ''
    elif isinstance(sym, Symbol):
        assert isinstance(sym.data, str), f'Symbol does not contain string: {sym}'
        sym = sym.data

    assert isinstance(sym, str), f'Input is not a string: {sym}'
    if sym == '.':
        return '<period>'
    else:
        return sym

def _sym_from_pyfoma (sym):
    if isinstance(sym, Symbol):
        return sym
    elif not isinstance(sym, str):
        raise Exception(f'Expecting a string: {repr(sym)}')
    elif sym == '.':
        return other
    elif sym == '<period>':
        return intern_symbol('.')
    elif not sym:
        return epsilon
    else:
        return intern_symbol(sym)

def _from_pyfoma (syms):
    return tuple(_sym_from_pyfoma(sym) for sym in syms if sym)

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

def _fst_str_lines (fst):
    if fst.initialstate.name != 1:
        yield f'*** Unexpected initial state {fst.initialstate.name}'
    for q in sorted(fst.states, key=lambda q:q.name):
        for (label, transitions) in sorted(q.transitions.items()):
            for trans in transitions:
                if len(trans.label) == 1:
                    insym = trans.label[0]
                    label = repr(_sym_from_pyfoma(insym))
                    yield f'E({q.name}, {label}, {trans.targetstate.name})'
                elif len(trans.label) == 2:
                    (i, o) = [repr(_sym_from_pyfoma(sym)) for sym in trans.label]
                    yield f'E({q.name}, {i}, {o}, {trans.targetstate.name})'
        if q in fst.finalstates:
            yield f'F({q.name})'

def _fst_str (fst):
    return '\n'.join(_fst_str_lines(fst))

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

def _fst_signature (fst):
    return (fst.initialstate.name,
            tuple(sorted(q.name for q in fst.finalstates)),
            tuple(sorted(_fst_transitions(fst))))

def _fsts_equal (fst1, fst2):
    if len(fst1.states) != len(fst2.states) or len(fst1.finalstates) != len(fst2.finalstates):
        return False
    qtab = {}
    todo = [(fst1.initialstate, fst2.initialstate)]
    while todo:
        (q1, q2) = todo.pop()
        if q1 in qtab:
            if qtab[q1] != q2:
                return False
        else:
            qtab[q1] = q2
            tab1 = q1.transitions
            tab2 = q2.transitions
            if len(tab1) != len(tab2):
                return False
            for (label, trs1) in tab1.items():
                if label not in tab2:
                    return False
                trs2 = tab2[label]
                assert len(trs1) == 1, 'FST1 is not determinized'
                assert len(trs2) == 1, 'FST2 is not determinized'
                for t1 in trs1:
                    for t2 in trs2:
                        if t1.weight != t2.weight:
                            return False
                        todo.append((t1.targetstate, t2.targetstate))
    # qtab is a one-one assignment
    # if the image of fst1.finalstates is a subset of fst2.finalstates, then they are equal,
    # because we already tested that the lengths are the same
    for q1 in fst1.finalstates:
        if q1 not in qtab:
            return False
        q2 = qtab[q1]
        if q2 not in fst2.finalstates:
            return False
    return True

def _pyfoma_compiler_cleanup (fst):
    '''
    This line was lifted from the PyFoma compiler (RegexParse.compile in pyfoma/private/regexparse.py).
    '''
    return fst.trim().epsilon_remove().push_weights().determinize_as_dfa().minimize_as_dfa().label_states_topology().cleanup_sigma()

# Start with the sole state-sequence that might produce a string of length 0.
# At each step, see if the last state is final. If so, output the state-sequence length minus one.
# Otherwise, expand: get the state-sequences that produce one more word.
# Do not create a state-sequence that contains a loop (the new state occurs already).
# If we end up with no state-sequences, then the fsa produces no output: return -1.
# The longest possible state-sequence will contain each state once.

def _fst_length (fst):
    '''
    The length of the shortest sentence. The fst must be determinized and minimized.
    '''
    qqs = [[fst.initialstate]]
    while qqs:
        new_qqs = []
        for qq in qqs:
            q = qq[-1]
            if q in fst.finalstates:
                return len(qq) - 1
            for transitions in q.transitions.values():
                for t in transitions:
                    dest = t.targetstate
                    if dest not in qq:
                        new_qqs.append(qq + [dest])
        qqs = new_qqs
    return -1


#--  Language  --------------------------------------------------------------

class Language:

    issymbol = False
    isstring = False
    istransducer = None
    isfinite = None

    precedence = None

    def __init__ (self):
        self._fst = None

    def __fst__ (self):
        '''
        Builds a NEW fst representing this language, to be owned by the caller.
        '''
        return NotImplemented

    def fst (self):
        '''
        This returns a pyfoma FST that belongs to this language. CAUTION: pyfoma
        operations are destructive! Call __fst__() instead, if you want an fst
        that you own.

        The FST is determinized and minimized (as an FSA).
        '''
        if self._fst is None:
            fst = self.__fst__()
            assert isinstance(fst, FST), f'Bad return from __fst__(): {repr(fst)}'
            self._fst = _pyfoma_compiler_cleanup(fst)
        return self._fst

    def to_fsa (self):
        '''
        This is the higher-level interface. The return value is a Language.
        '''
        return FSA(self.fst(), self.istransducer)

    def __len__ (self):
        return _fst_length(self.fst())

    def __hash__ (self):
        return hash(_fst_signature(self.fst()))

    def __eq__ (self, other):
        assert isinstance(other, Language), f'Not a Language: {other}'
        return _fst_signature(self.fst()) == _fst_signature(other.fst())

#     def __eq__ (self, other):
#         assert isinstance(other, Language), f'Not a Language: {other}'
#         if self.istransducer:
#             if other.istransducer:
#                 raise Exception('Cannot test equality of transducers')
#             else:
#                 return False
#         elif other.istransducer:
#             return False
#         else:
#             return _fsts_equal(self.fst(), other.fst())

    def __bool__ (self):
        try:
            next(self.__iter__())
            return True
        except StopIteration:
            return False

    def __iter__ (self):
        return iter(FSA(self.fst(), self.istransducer))

    def __contains__ (self, x):
        return self.to_fsa().__contains__(x)

    def __call__ (self, x):
        return self.to_fsa()(x)

    def inv (self, x):
        return self.to_fsa().inv(x)

    def __add__ (self, other):
        other = to_language(other)
        return Union([self, other])

    def __sub__ (self, other):
        other = to_language(other)
        return Difference([self, other])

    def __mul__ (self, other):
        other = to_language(other)
        return Concatenation([self, other])

    def __rmul__ (self, other):
        other = to_language(other)
        return Concatenation([other, self])

    def __truediv__ (self, other):
        other = to_language(other)
        return CrossProduct([self, other])

    def __rtruediv__ (self, other):
        other = to_language(other)
        return CrossProduct([other, self])

    def __matmul__ (self, other):
        other = to_language(other)
        return Composition([self, other])

    def __rmatmul__ (self, other):
        other = to_language(other)
        return Composition([other, self])

#     # not used
#     def __set__ (self):
#         if self.isfinite:
#             return frozenset(iter(self))
#         else:
#             return NotImplemented

    def parenthesize (self, x):
        '''
        If x's operator has greater precedence than mine or if x's type
        is the same as mine, then no parens are needed.
        '''
        if x.precedence is None or self.precedence is None:
            raise Exception(f'Missing precedence! {repr(self), repr(x)}')
        if x.precedence > self.precedence or type(x) == type(self):
            return x.__bare__()
        else:
            return '(' + x.__bare__() + ')'

    def to_sequence (self):
        raise Exception(f'Cannot be converted to a sequence: {repr(self)}')

    def to_symbol (self):
        raise Exception(f'Cannot be converted to a symbol: {repr(self)}')

    def __repr__ (self):
        '''
        When defining a subclass of Language, define __bare__, not __repr__.
        '''
        return self.__bare__()


def to_language (x):
    if isinstance(x, Language):
        return x
    elif isinstance(x, Value):
        return Union(x.atoms)
    elif isinstance(x, (tuple, list)):
        return Concatenation(x)
    elif isinstance(x, (set, frozenset)):
        return Union(x)
    else:
        return Symbol(x)


def L (*args):
    if len(args) > 1:
        return to_language(args)
    elif len(args) == 0:
        return empty
    else:
        return to_language(args[0])


#--  Symbol  -------------------------------------------------------------------

def is_identifier (x):
    return (
        len(x) > 0 and
        (x[0].isalpha() or x[0] == '_') and
        all(c.isalnum() or c == '_' for c in x[1:])
    )


class Symbol (Language):

    precedence = 0

    def __init__ (self, x):
        Language.__init__(self)
        self.data = x

    def __hash__ (self):
        return hash(self.data)

    def __eq__ (self, other):
        if isinstance(other, Symbol):
            return self.data == other.data
        elif isinstance(other, str):
            return self.data == other
        else:
            return False

    def __lt__ (self, other):
        if isinstance(other, Symbol):
            return self.data < other.data
        elif isinstance(other, str):
            return self.data < other
        else:
            raise Exception(f'Cannot compare Symbol and {type(other)}')

    def __fst__ (self):
        return FST(label=(_sym_to_pyfoma(self.data),))

    def __bare__ (self):
        if isinstance(self.data, str):
            if not is_identifier(self.data):
                return repr(self.data)
            else:
                return self.data
        else:
            return repr(self.data)

    def to_symbol (self):
        return self

    def to_sequence (self):
        return tuple([self.data])

    def __getitem__ (self, *ftrs):
        return Category([self.data, *ftrs])


symbols = Namespace(Symbol)
intern_symbol = symbols


#--  Atoms  --------------------------------------------------------------------

from .features import Value, variables, ANY, NULL

def _value_to_atom (v):
    if len(v.atoms) == 0:
        return EmptyLanguage()
    elif len(v.atoms) == 1:
        return Symbol(v.atoms[0])
    else:
        raise Exception('Attempt to coerce an ambiguous Value to a Symbol')

Value.__to_language__ = _value_to_atom


#--  Words, letters, vocab, alphabet  ------------------------------------------

def words (s):
    assert isinstance(s, str), 'Input must be a quoted string'
    return Concatenation(intern_symbol(x) for x in s.split())

def letters (s):
    assert isinstance(s, str), 'Input must be a quoted string'
    return Concatenation(intern_symbol(x) for x in s)

def vocab (*words):
    if len(words) == 1:
        if isinstance(words[0], types.GeneratorType):
            words = list(words[0])
        elif isinstance(words[0], (tuple, list)):
            words = words[0]
        elif isinstance(words[0], str):
            words = words[0].split()
        else:
            raise Exception(f'Expecting words, got {words[0]}')
    assert all(isinstance(word, str) for word in words), 'Vocabulary elements must be quoted'
    assert all(' ' not in word for word in words), 'Vocabulary elements cannot contain spaces'
    return set(intern_symbol(w) for w in words)

def alphabet (*letters):
    if len(letters) == 1:
        if isinstance(letters[0], types.GeneratorType):
            letters = list(letters[0])
        else:
            letters = letters[0]
    assert all(isinstance(letter, str) for letter in letters), 'Alphabet elements must be quoted'
    assert all(len(letter) == 1 for letter in letters), 'Alphabet elements must be single letters'
    return set(intern_symbol(ltr) for ltr in letters)


class IterableCall:

    def __init__ (self, f, *args, **kwargs):
        self.f = f
        self.args = args
        self.kwargs = kwargs

    def __iter__ (self):
        return iter(self.f(*self.args, **self.kwargs))


class Enumeration (Language):
    '''
    The argument to an Enumeration must be an iterable, not an iteration.
    That is, it is not simply a function that uses yield, but rather an
    object that provides an __iter__ method. A Language is suitable, as is
    an IterableCall.
    '''

    @staticmethod
    def seqlen (x):
        if isinstance(x, tuple) and len(x) > 0 and isinstance(x[0], (tuple, list)):
            return sum(len(elt) for elt in x)
        else:
            return len(x)

    def __init__ (self, x, n=10):
        self.arg = x
        self.truncate_at = n
        
    def __bool__ (self):
        g = iter(self.arg)
        try:
            next(g)
            return True
        except StopIteration:
            return False

    def __getitem__ (self, tgt):
        if tgt < 0:
            n = -tgt
            lst = []
            ptr = 0
            for item in self.arg:
                if len(lst) < n:
                    lst.append(item)
                    ptr += 1
                else:
                    if ptr >= n:
                        ptr = 0
                    lst[ptr] = item
                    ptr += 1
            if len(lst) < n:
                raise IndexError('List index out of range')
            return lst[ptr-1]
        else:
            for (i, elt) in enumerate(self.arg):
                if i == tgt:
                    return elt

    def __len__ (self):
        n = 0
        for _ in self.arg:
            n += 1
        return n

    def __iter__ (self):
        return iter(self.arg)

    def _words (self):
        for (i, elt) in enumerate(self.arg):
            if i >= self.truncate_at:
                yield '...'
                break
            else:
                yield(f'[{i}] {elt}')

    def __repr__ (self):
        s = '\n'.join(self._words())
        if s:
            return s
        else:
            return '<empty enumeration>'


#     def __init__ (self, x, n=10):
#         self.arg = x
#         elts = []
#         self.truncated = False
#         for (i, elt) in enumerate(x):
#             if i >= n:
#                 self.truncated = True
#                 break
#             elts.append(elt)
#         elts.sort(key=repr)
#         elts.sort(key=self.seqlen)
#         self.elts = elts
#
#     def __bool__ (self):
#         return bool(self.elts)
# 
#     def __getitem__ (self, i):
#         return self.elts[i]
# 
#     def __len__ (self):
#         return len(self.elts)
# 
#     def __iter__ (self):
#         return iter(self.elts)
# 
#     def _words (self):
#         for (i, elt) in enumerate(self.elts):
#             yield(f'[{i}] {elt}')
#         if self.truncated:
#             yield '...'
# 
#     def __repr__ (self):
#         s = '\n'.join(self._words())
#         if s:
#             return s
#         else:
#             return '<empty enumeration>'


def enum (x, n=10):
    return Enumeration(x, n)


# class String:
#     '''
#     Created by concatenating Atoms or Strings.
#     '''
#     
#     def __init__ (self, items):
#         if not (isinstance(items, tuple) and all(isinstance(item, Atom) for item in items)):
#             raise Exception('Initializer for String must be tuple of Atoms')
#         self.data = items
# 
#     def __mul__ (self, other):
#         if isinstance(other, Atom):
#             return String(self.data + (other,))
#         elif isinstance(other, String):
#             return String(self.data + other.data)
#         else:
#             return Concatenation((self, other))
# 
#     def __rmul__ (self, other):
#         other = coerce(other, Language)
#         return other * self
# 
#     def __bare__ (self):
#         words = [item.__bare__() for item in self.data]
#         if words:
#             return LANGLE + ', '.join(words) + RANGLE
#         else:
#             return EPSILON


class LgFunction:

    def __getattr__ (self, name):
        if name == 'epsilon':
            return Concatenation([])
        elif name == 'empty':
            return EmptyLanguage()
        else:
            return Symbol(name)

    def __call__ (self, *args):
        if len(args) == 0:
            raise Exception('At least one argument must be provided')
        elif len(args) == 1:
            return to_language(args[0])
        else:
            return [to_language(arg) for arg in args]

#         atoms = list(self._create_atoms(names))
#         return atoms[0] if len(atoms) == 1 else atoms

#     def _create_atoms (self, names):
#         if isinstance(names, str):
#             yield self.create_atom(names)
#         else:
#             for name in names:
#                 yield from self.create_atoms(name)
# 
#     def _create_atom (self, name):
#         if name == 'epsilon':
#             return Concatenation([])
#         elif name == 'empty':
#             return EmptyLanguage()
#         else:
#             return Atom(name)


def var (*names):
    if len(names) == 1:
        assert isinstance(names[0], str), 'Argument to var must be a quoted string'
        return Variable(names[0])
    else:
        return [Variable(name) for name in names]


class Other (Language):

    precedence = 0

    def __init__ (self):
        Language.__init__(self)
        self.istransducer = False
        self.isfinite = True

    def __fst__ (self):
        return FST(label=('.',))

    def __bare__ (self):
        return 'other'

    def to_symbol (self):
        return self

    def to_sequence (self):
        return tuple([self])


class EmptyLanguage (Language):

    precedence = 0

    def __init__ (self):
        Language.__init__(self)
        self.data = set()

    def __fst__ (self):
        return FST()

    def __bare__ (self):
        return EMPTYSET


def _union_elements (args):
    for arg in args:
        arg = to_language(arg)
        if isinstance(arg, Union):
            yield from arg.args
        else:
            yield arg


class Union (Language):

    precedence = -4

    def __init__ (self, args):
        Language.__init__(self)
        self.args = tuple(to_language(x) for x in args)
        self.istransducer = any(arg.istransducer for arg in self.args)
        self.isfinite = all(arg.isfinite for arg in self.args)
        
    def __fst__ (self):
        fst = self.args[0].__fst__()
        for x in self.args[1:]:
            fst = fst.union(x.__fst__())
        return fst
        
    def __bare__ (self):
        if len(self.args) > 1:
            return ' + '.join(sorted(self.parenthesize(arg) for arg in self.args))
        elif len(self.args) == 1:
            return list(self.args)[0].__bare__()
        else:
            return EMPTYSET


class CharRange (Language):

    precedence = 0

    def __init__ (self, c1, c2):
        Language.__init__(self)
        i = ord(str(c1))
        j = ord(str(c2))+1
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

    precedence = -4

    def __init__ (self, args):
        Language.__init__(self)
        assert len(args) > 0, 'Difference requires arguments'
        self.args = tuple(to_language(x) for x in args)
        self.istransducer = self.args[0].istransducer
        self.isfinite = self.args[0].isfinite
        
    def __fst__ (self):
        fst = self.args[0].__fst__()
        for x in self.args[1:]:
            fst = fst.difference(x.__fst__())
        return fst
        
    def __bare__ (self):
        if len(self.args) > 1:
            return ' - '.join(self.parenthesize(arg) for arg in self.args)
        elif len(self.args) == 1:
            return self.args[0].__bare__()
        else:
            raise Exception('This cannot happen')


def is_string (x):
    return isinstance(x, Concatenation) and x.isstring

def string (x):
    '''
    Converts a Symbol or Concatenation to a tuple of Symbols.
    '''
    if isinstance(x, Symbol):
        return tuple(x)
    elif is_string(x):
        return x.to_sequence()


class Concatenation (Language):

    precedence = -3

    def __init__ (self, args):
        Language.__init__(self)
        self.args = tuple(to_language(arg) for arg in args)
        self.isstring = all(isinstance(arg, Symbol) or is_string(arg) for arg in self.args)
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
            return CDOT.join(self.parenthesize(arg) for arg in self.args)
        elif len(self.args) == 1:
            return self.args[0].__bare__()
        else:
            return EPSILON

    def to_sequence (self):
        return tuple(self._symbols())

    def _symbols (self):
        for arg in self.args:
            if isinstance(arg, Concatenation):
                yield from arg._symbols()
            else:
                yield arg.to_symbol()


def concat (*args):
    return Concatenation(args)


class KleeneClosure (Language):

    precedence = -2

    def __init__ (self, arg):
        Language.__init__(self)
        self.arg = to_language(arg)
        self.istransducer = self.arg.istransducer
        self.isfinite = False
        
    def __fst__ (self):
        return self.arg.__fst__().kleene_closure()
        
    def __bare__ (self):
        return self.parenthesize(self.arg) + '*'


def star (x):
    return KleeneClosure(x)

def repeat (x):
    return Concatenation([x, KleeneClosure(x)])


class Optional (Language):

    precedence = -2

    def __init__ (self, arg):
        Language.__init__(self)
        self.arg = to_language(arg)
        self.transducer = self.arg.istransducer
        self.isfinite = self.arg.isfinite

    def __fst__ (self):
        return self.arg.__fst__().optional()

    def __bare__ (self):
        return self.arg.__bare__() + '?'


def opt (x):
    return Optional(x)


class CrossProduct (Language):

    precedence = -1

    def __init__ (self, args):
        Language.__init__(self)
        self.args = tuple(to_language(x) for x in args)
        self.istransducer = True
        self.isfinite = all(arg.isfinite for arg in self.args)

    def __fst__ (self):
        if len(self.args) != 2:
            raise Exception('Cross product (:) requires exactly two arguments')
        return self.args[0].__fst__().cross_product(self.args[1].__fst__())

    def __bare__ (self):
        return self.parenthesize(self.args[0]) + ':' + self.parenthesize(self.args[1])


def io (x, y):
    return CrossProduct([x,y])


class Composition (Language):

    precedence = -15

    def __init__ (self, args):
        assert isinstance(args, (list, tuple)) and len(args) > 0, 'Composition requires at least one argument'
        Language.__init__(self)
        self.args = tuple(to_language(x) for x in args)
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

    precedence = -13

    def __init__ (self, x, y, after=None, before=None):
        Language.__init__(self)
        self.x = to_language(x)
        self.y = to_language(y)
        self.after = Concatenation([]) if after is None else to_language(after)
        self.before = Concatenation([]) if before is None else to_language(before)
        self.istransducer = True
        self.isfinite = False

    def __fst__ (self):
        fst = io(self.x, self.y).fst()
        left = self.after.fst()
        right = self.before.fst()
        return fst.rewrite((left, right))

    def __bare__ (self):
        x = self.parenthesize(self.x)
        y = self.parenthesize(self.y)
        left = self.parenthesize(self.after)
        right = self.parenthesize(self.before)
        return f'{x} {RIGHTARROW} {y} / {left} _ {right}'


#--  FSABuilder  ---------------------------------------------------------------

class FSABuilder:

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

    def E (self, *args):
        if len(args) == 2:
            (q1, q2) = args
            label = ('',)
        elif len(args) == 3:
            (q1, insym, q2) = args
            label = (_sym_to_pyfoma(insym),)
        elif len(args) == 4:
            (q1, insym, outsym, q2) = args
            label = (_sym_to_pyfoma(insym), _sym_to_pyfoma(outsym))
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

    precedence = 0

    def __init__ (self, fst, istransducer):
        '''
        The FSA will not call any destructive operations on fst, so it is fine to
        pass in an FST that you own.
        '''
        if fst is None: raise Exception('No fst')
        Language.__init__(self)
        self._fst = fst
        self.istransducer = self.compute_istransducer() if istransducer is None else istransducer

    def __fst__ (self):
        '''
        This returns a copy, which now belongs to the caller.
        '''
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
        x = _to_input_tuple(x)
        fst = self._fst
        fst.tokenize_against_alphabet = lambda x: x
        insyms = [_sym_to_pyfoma(sym) for sym in x]
        fnc = fst.analyze if invert else fst.generate
        return (_from_pyfoma(y) for y in fnc(insyms, tokenize_outputs=True))

    def __call__ (self, x, invert=False):
        out = Enumeration(IterableCall(self._call, x, invert=invert))
        return out if self.istransducer else bool(out)

    def inv (self, x):
        return self.__call__(x, invert=True)

    def __contains__ (self, x):
        try:
            next(self._call(x))
            return True
        except StopIteration:
            return False

    def __graph__ (self):
        return self._fst.view()

    def __bare__ (self):
        a = 'T' if self.istransducer else 'A'
        return f'<FS{a} with {len(self._fst.states)} states>'

    def __str__ (self):
        s = _fst_str(self.fst())
        if s:
            return s
        else:
            return '<empty fsa>'


class Inversion (Language):

    precedence = -2

    def __init__ (self, arg):
        self.arg = to_language(arg)

    def __fst__ (self):
        if isinstance(self.arg, Inversion):
            return self.arg.arg.__fst__()
        else:
            return self.arg.__fst__().inv()

    def __call__ (self, x, invert=False):
        if isinstance(self.arg, Inversion):
            return self.arg.arg.__call__(x, invert=invert)
        elif isinstance(self.arg, FSA):
            return self.arg.__call__(x, invert=not invert)
        else:
            fsa = self.arg.to_fsa()
            return fsa.__call__(x, invert=not invert)

    def __bare__ (self):
        return self.parenthesize(self.arg) + SUPMINUS + SUPONE


def graph (x):
    if hasattr(x, '__graph__'):
        return x.__graph__()
    else:
        raise Exception('Not drawable')



#--  Coercion  -----------------------------------------------------------------

class CoercionError (ValueError): pass

class Coercion:

    coercions = {frozenset: [ ((builtins.set, list, tuple, types.GeneratorType), frozenset),
                              (object, lambda x: frozenset([x])) ],
                 Symbol: [ ((str, int, float, tuple), Symbol) ],
                 Language: [ (str,),
                                (Value, Value.__to_language__),
                                ((tuple, list), lambda x: Concatenation(x)),
                                ((set, frozenset), Union) ]
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


#--  Pseudo-package  -----------------------------------------------------------

# see autosym.py
__path__ = ['autosym::']

#--  Globals  ------------------------------------------------------------------

coerce = Coercion()
epsilon = Concatenation([])
empty = EmptyLanguage()
_fsa_builder = FSABuilder()
E = _fsa_builder.E
F = _fsa_builder.F
done = _fsa_builder.make_fsa
erase_fsa = _fsa_builder.erase_fsa
edit = _fsa_builder.edit_fsa
lg = LgFunction()
other = Other()
rewrite = RewriteRule
invert = Inversion
union = Union
