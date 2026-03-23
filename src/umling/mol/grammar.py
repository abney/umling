
from .lang import Language, Symbol, Category, Variable, Value
from .io import PrettyString


def grule (lhs, *rhs, cost=0):
    return GrammarRule(lhs, tuple(rhs), cost)


class GrammarRule:

    def __init__ (self, lhs, rhs, cost=0):
        self.lhs = lhs.cat
        assert isinstance(self.lhs, Category)
        self.rhs = rhs
        self.bindings = {}
        self.cost = cost
        
        for cat in (self.lhs,) + self.rhs:
            if isinstance(cat, Category):
                for v in cat.features:
                    if isinstance(v, Variable) and v not in self.bindings:
                        self.bindings[v] = Value.top

    def __mul__ (self, cat):
        return PartialMatch(self) * cat

    def __repr__ (self):
        return f"{repr(self.lhs)} -> {' '.join(repr(c) for c in self.rhs)}"


class PartialMatch:

    def __init__ (self, grule, n=0, bindings=None, expansion=None):
        if bindings is None:
            bindings = grule.bindings

        self._grule = grule
        self._n = n
        self._bindings = bindings
        self._expansion = [] if expansion is None else expansion

    def __getattr__ (self, attr):
        if attr in {'grule', 'n', 'bindings', 'expansion'}:
            return getattr(self, '_' + attr)
        elif attr == 'i':
            return self._expansion[0].i
        elif attr == 'j':
            return self._expansion[-1].j
        elif attr == 'cost':
            return self.grule.cost
        else:
            raise AttributeError('No such attribute')

    def is_complete (self):
        return self.n >= len(self.grule.rhs)

    def expecting (self):
        if self.n < len(self.grule.rhs):
            return self.grule.rhs[self.n]

    def __mul__ (self, child):
        if self.is_complete():
            return None
        r = self.grule
        rule_childcat = r.rhs[self.n]
        if isinstance(child, Symbol):
            if child == rule_childcat:
                return PartialMatch(r, self.n+1, self.bindings, self.expansion + [child])
        else:
            # unify is destructive; we need a fresh set of bindings
            bindings = dict(self.bindings)
            chcat = r.rhs[self.n].unify(child.cat, bindings)
            if chcat:
                child = child.clone(cat=chcat)
                return PartialMatch(r, self.n+1, bindings, self.expansion + [child])

    def reduce (self):
        b = self.bindings
        r = self.grule
        lhs = r.lhs.bind(b)
        return Node(lhs, self.expansion)

    def __repr__ (self):
        lhs = self.grule.lhs
        rhs = self.grule.rhs
        n = self.n
        predot = [repr(child) if isinstance(child, Symbol) else repr(child.cat)
                  for child in self.expansion]
        postdot = [repr(x) for x in rhs[n:]]
        return ' '.join([repr(lhs), '->'] + predot + ['*'] + postdot)


def _append_value (d, k, v):
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]


class Grammar (Language):

    def __init__ (self, rules=[]):
        self.rules = rules
        self._by_lhs = {}
        self._by_rhs = {}
        self._empty_rules = []
        self._first_tab = {}
        self._terminals = None

        self._build_index()
        self._fix_categories()
        self._compute_terminals()

    def _build_index (self):
        for r in self.rules:
            _append_value(self._by_lhs, r.lhs.symbol, r)
            if r.rhs:
                _append_value(self._by_rhs, r.rhs[0].symbol, r)
            else:
                self._empty_rules.append(r)

    def _fix_categories (self):
        for i in range(len(self.rules)):
            r = self.rules[i]
            lhs = r.lhs.cat if isinstance(r.lhs, Symbol) else r.lhs
            assert isinstance(lhs, Category)
            rhs = tuple(cat if isinstance(cat, Symbol) and cat not in self._by_lhs else cat.cat
                        for cat in r.rhs)
            for x in rhs:
                assert isinstance(x, Symbol) or isinstance(x, Category)
            self.rules[i] = GrammarRule(lhs, rhs, r.cost)

    def _compute_terminals (self):
        terms = set()
        for r in self.rules:
            for x in r.rhs:
                if isinstance(x, Symbol):
                    terms.add(x)
        self._terminals = terms

    def terminals (self):
        return self._terminals

    def nonterminals (self):
        return self._by_lhs.keys()

    def is_terminal (self, x):
        return x in self._terminals

    def expansions (self, cat):
        return self._by_lhs.get(cat.symbol, [])

    def continuations (self, cat):
        return self._by_rhs.get(cat.symbol, [])

    def _compute_nullable (self):
        pass

    def first (self, X):
        if isinstance(X, Symbol):
            if X in self._terminals:
                return [X]
            elif X in self._by_lhs:
                X = X.cat
            else:
                raise Exception('Unrecognized symbol')
        assert isinstance(X, Category)
        X = X.bind()
        if X in self._first_tab:
            return self._first_tab[X]
        else:
            self._first_tab[X] = set(self._compute_first([X]))
            return self._first_tab[X]

    def _compute_first (self, computing):
        X = computing[-1]
        assert isinstance(X, Category)
        for r in self.rules:
            bindings = {}
            if r.lhs.unify(X, bindings):
                first = r.rhs[0]
                if isinstance(first, Symbol):
                    yield first
                else:
                    first = first.bind(bindings)
                    # if it's on our stack, break the cycle
                    if first not in computing:
                        yield first
                        if first in self._first_tab:
                            yield from self._first_tab[first]
                        elif first not in self._terminals:
                            yield from self._compute_first(computing + [first])
                
    def first_terminals (self, X):
        return [t for t in self.first(X) if isinstance(t, Symbol)]

    def generate_from (self, cat):
        if isinstance(cat, Symbol):
            cat = Category(cat)
        return self._generate_from(cat)

    def _generate_from (self, cat):
        assert isinstance(cat, Category)
        rules = self.expand(cat)
        if rules:
            for r in rules:
                bindings = {}
                lhs = r.lhs.unify(cat, bindings)
                if lhs:
                    for (subtrees, exp_bindings) in self._generate_subtrees([], r.rhs, bindings):
                        yield Node(lhs.bind(exp_bindings), subtrees)
        else:
            yield cat

    def _generate_subtrees (self, subtrees, cats, bindings):
        if not cats:
            yield (subtrees, bindings)
        elif self.is_terminal(cats[0]):
            yield from self._generate_subtrees(subtrees + [cats[0]], cats[1:], bindings)
        else:
            cat = cats[0].bind(bindings)
            assert cat.is_variable_free()
            for node in self.generate_from(cat):
                exp_bindings = dict(bindings)
                if cat.unify(node.cat, exp_bindings):
                    yield from self._generate_subtrees(subtrees + [node], cats[1:], exp_bindings)

    def __str__ (self):
        return '\n'.join(repr(r) for r in self.rules)


class GrammarBuilder:

    def __init__ (self):
        self.rules = []

    def R (self, lhs, *rhs, cost=0):
        self.rules.append(GrammarRule(lhs, rhs, cost))

    def done (self):
        g = Grammar(self.rules)
        self.rules = []
        return g

    def edit (self, grammar):
        self.rules = grammar.rules


class Node:

    def __init__ (self, cat, children, i=-1, j=-1, sem=None):
        self._cat = cat
        self._children = children
        self._i = i
        self._j = j
        self._sem = sem

    def clone (self, cat=None):
        if cat is None: cat = self._cat
        return Node(cat, self._children, self._i, self._j, self._sem)

    def __getattr__ (self, attr):
        if attr in {'cat', 'children', 'i', 'j', 'sem'}:
            return getattr(self, '_' + attr)

    def __repr__ (self):
        return f'{self.cat.symbol}({self.i}:{self.j})'

    def _print_recurse (self, node, pprint):
        if not isinstance(node, Node):
            pprint(node)
        else:
            pprint(node._cat)
            if node._children:
                with pprint.indent():
                    for child in node._children:
                        self._print_recurse(child, pprint)

    def __str__ (self):
        with PrettyString() as pprint:
            self._print_recurse(self, pprint)
        return str(pprint).rstrip('\n')


# class PartialMatch:
# 
#     def __init__ (self, prev, rule, expansion, bindings):
#         self.prev = prev
#         self.rule = rule
# 
#         ##  The children collected so far.
#         self.expansion = expansion
# 
#         ##  Current bindings.
#         self.bindings = bindings
#         timestep += 1
# 
#         ##  Sequence number.  Nodes and edges are numbered in the order created.
#         self.timestep = timestep
# 
#     ##  String representation.
# 
#     def __repr__ (self):
#         s = '(' + str(self.rule.lhs) + ' ->'
#         for node in self.expansion:
#             s += ' ' + str(node)
#         s += ' *'
#         for cat in self.rule.rhs[len(self.expansion):]:
#             s += ' ' + str(cat)
#         s += ' {'
#         s += ' '.join(str(val) for val in self.bindings)
#         s += '})'
#         return s
# 
#     ##  Rule lhs.
# 
#     def cat (self):
#         return self.rule.lhs
# 
#     ##  Start position of first child.
# 
#     def start (self):
#         return self.expansion[0].i
# 
#     ##  End position of last child so far.
# 
#     def end (self):
#         return self.expansion[-1].j
# 
#     ##  Category after the dot.
# 
#     def afterdot (self):
#         n = len(self.expansion)
#         if n < len(self.rule.rhs):
#             return self.rule.rhs[n]
#         else:
#             return None
# 
#     ##  Fuse the semantics with the semantics of the given children.
# 
#     def reduce (self, children):
#         sem = self.rule.sem
#         if sem and hasattr(sem, '__call__'):
#             return sem([c.sem for c in children])
#         else:
#             return sem

class Parser:

    pass
