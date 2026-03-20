

class Node:

    def __init__ (self, cat, i=-1, j=-1, expansion=None, sem=None):
        self._cat = cat
        self._i = i
        self._j = j
        self._expansion = expansion
        self._sem = sem

    def __getattr__ (self, attr):
        if attr in {'cat', 'i', 'j', 'expansion', 'sem'}:
            return getattr(self, '_' + attr)

    def __repr__ (self):
        return f'{self.cat.symbol}({self.i}:{self.j})'


class PartialMatch:

    def __init__ (self, prev, rule, expansion, bindings):
        self.prev = prev
        self.rule = rule

        ##  The children collected so far.
        self.expansion = expansion

        ##  Current bindings.
        self.bindings = bindings
        timestep += 1

        ##  Sequence number.  Nodes and edges are numbered in the order created.
        self.timestep = timestep

    ##  String representation.

    def __repr__ (self):
        s = '(' + str(self.rule.lhs) + ' ->'
        for node in self.expansion:
            s += ' ' + str(node)
        s += ' *'
        for cat in self.rule.rhs[len(self.expansion):]:
            s += ' ' + str(cat)
        s += ' {'
        s += ' '.join(str(val) for val in self.bindings)
        s += '})'
        return s

    ##  Rule lhs.

    def cat (self):
        return self.rule.lhs

    ##  Start position of first child.

    def start (self):
        return self.expansion[0].i

    ##  End position of last child so far.

    def end (self):
        return self.expansion[-1].j

    ##  Category after the dot.

    def afterdot (self):
        n = len(self.expansion)
        if n < len(self.rule.rhs):
            return self.rule.rhs[n]
        else:
            return None

    ##  Fuse the semantics with the semantics of the given children.

    def reduce (self, children):
        sem = self.rule.sem
        if sem and hasattr(sem, '__call__'):
            return sem([c.sem for c in children])
        else:
            return sem

class Parser:

    pass
