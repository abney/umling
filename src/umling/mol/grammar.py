
from .lang import Category, Variable, Value


def grule (lhs, *rhs, cost=0):
    return GrammarRule(lhs, tuple(rhs), cost)


class GrammarRule:

    def __init__ (self, lhs, rhs, cost=0):
        self.lhs = lhs
        self.rhs = rhs
        self.bindings = {}
        self.cost = cost
        
        for cat in (lhs,) + rhs:
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
        if n < len(grule.rhs):
            cat = None
        else:
            ftrs = tuple(v if not isinstance(v, Variable) else bindings[v]
                         for v in grule.lhs.features)
            cat = Category(grule.lhs.symbol, ftrs)

        self._grule = grule
        self._n = n
        self._bindings = bindings
        self._expansion = [] if expansion is None else expansion
        self._cat = cat

    def __getattr__ (self, attr):
        if attr in {'grule', 'n', 'bindings', 'expansion', 'cat'}:
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

    def __mul__ (self, child):
        if self.is_complete():
            return None
        r = self.grule
        rule_childcat = r.rhs[self.n]
        # _unify is destructive; we need a fresh set of bindings
        bindings = dict(self.bindings)
        if rule_childcat._unify(child.cat, bindings):
            return PartialMatch(r, self.n+1, bindings, self.expansion + [child])

    def __repr__ (self):
        lhs = self.grule.lhs
        rhs = self.grule.rhs
        n = self.n
        predot = ' '.join(repr(c) for c in rhs[:n])
        postdot = ' '.join(repr(c) for c in rhs[n:])
        return f"{repr(lhs)} -> {predot} * {postdot}"


def _append_value (d, k, v):
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]


class Grammar:

    def __init__ (self, rules=[]):
        self.rules = rules
        self._by_lhs_symbol = {}
        self._by_rhs_symbol = {}
        self._empty_rules = []
        self._build_index()

    def _build_index (self):
        for r in self.rules:
            _append_value(self._by_lhs_symbol, r.lhs.symbol, r)
            if r.rhs:
                _append_value(self._by_rhs_symbol, r.rhs[0].symbol, r)
            else:
                self._empty_rules.append(r)

    def expand (self, cat):
        return self._by_lhs_symbol.get(cat.symbol, [])

    def continuations (self, cat):
        return self._by_rhs_symbol.get(cat.symbol, [])


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

