
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

    def __init__ (self, grule, i=0, bindings=None):
        if bindings is None:
            bindings = grule.bindings

        self.grule = grule
        self.i = i
        self.bindings = bindings

    def is_complete (self):
        return self.i >= len(self.grule.rhs)

    def __mul__ (self, chcat):
        r = self.grule
        if self.is_complete():
            return None
        rcat = r.rhs[self.i]
        bindings = dict(self.bindings)
        if rcat._unify(chcat, bindings):
            return PartialMatch(r, self.i+1, bindings)

    def cat (self):
        r = self.grule
        if not self.is_complete():
            return None
        bindings = self.bindings
        ftrs = tuple(v if not isinstance(v, Variable) else bindings[v]
                     for v in r.lhs.features)
        return Category(r.lhs.symbol, ftrs)

    def cost (self):
        return self.grule.cost

    def __repr__ (self):
        lhs = self.grule.lhs
        rhs = self.grule.rhs
        i = self.i
        predot = ' '.join(repr(c) for c in rhs[:i])
        postdot = ' '.join(repr(c) for c in rhs[i:])
        return f"{repr(lhs)} -> {predot} * {postdot}"
