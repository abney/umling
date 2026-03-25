
import random
from heapq import heappush, heappop
from .lang import Language, Symbol, Category, Variable, Value, string, intern_symbol
from .io import PrettyString, PrettyPrinter


def grule (lhs, *rhs, cost=0):
    return Rule(lhs, tuple(rhs), cost)


class Node:

    def __init__ (self, cat, children, rule=None, i=-1, j=-1, cost=0, sem=None):
        self._cat = cat
        self._children = children
        self._rule = rule
        self._i = i
        self._j = j
        self._cost = cost
        self._sem = sem

    def clone (self, cat=None):
        if cat is None: cat = self._cat
        return Node(cat, self._children, self._rule, self._i, self._j, self._cost, self._sem)

    def __getattr__ (self, attr):
        if attr in {'cat', 'children', 'rule', 'i', 'j', 'cost', 'sem'}:
            return getattr(self, '_' + attr)

    def __repr__ (self):
        return f'{self.cat.symbol}({self.i}:{self.j})'

    def __str__ (self):
        with PrettyString() as pprint:
            self._pretty_print(self, pprint)
        return str(pprint).rstrip('\n')

    def _pretty_print (self, node, pprint):
        if isinstance(node, (Symbol, str)):
            pprint(node)
        else:
            pprint(node.cat)
            with pprint.indent():
                for child in node.children:
                    self._pretty_print(child, pprint)


class Rule:

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

    def is_preterminal (self):
        return all(isinstance(x, Symbol) for x in self.rhs)

    def start (self):
        return Partial(self, 0, self.bindings, [])

    def shift (self, i):
        assert len(self.rhs) == 1 and isinstance(self.rhs[0], Symbol)
        return Node(self.lhs, self.rhs, self, i, i+1, self.cost)

    def topdown (self, cat):
        b = {}
        if self.lhs.unify(cat, b):
            return Partial(self, 0, b, [])

    def __repr__ (self):
        return f"{repr(self.lhs)} -> {' '.join(repr(c) for c in self.rhs)}"


class Partial:

    def __init__ (self, rule, n, bindings, children):
        self._rule = rule
        self._n = n
        self._bindings = bindings
        self._children = children

    def __getattr__ (self, attr):
        if attr in {'rule', 'n', 'bindings', 'children'}:
            return getattr(self, '_' + attr)
        elif attr == 'i':
            return self._children[0].i if self._children else self._i
        elif attr == 'j':
            return self._children[-1].j if self._children else self._i + 1
        else:
            raise AttributeError('No such attribute')

    def is_complete (self):
        return self.n >= len(self.rule.rhs)

    def expectation (self):
        if self.n < len(self.rule.rhs):
            nextcat = self.rule.rhs[self.n]
            return nextcat.bind(self.bindings)

    def __mul__ (self, child):
        assert isinstance(child, Node)
        if self.is_complete():
            return None
        b = dict(self.bindings)
        cat = self.rule.rhs[self.n]
        cat = cat.unify(child.cat, b)
        if cat:
            child = child.clone(cat=cat)
            return Partial(self.rule, self.n+1, b, self.children + [child])

    def reduce (self):
        r = self.rule
        cat = r.lhs.bind(self.bindings)
        cost = r.cost + sum(child.cost for child in self.children)
        return Node(cat, self.children, r, self.i, self.j, cost)

    def __repr__ (self):
        lhs = self.rule.lhs
        rhs = self.rule.rhs
        n = self.n
        predot = [repr(child) if isinstance(child, Symbol) else repr(child.cat)
                  for child in self.children]
        postdot = [repr(x) for x in rhs[n:]]
        return ' '.join([repr(lhs), '->'] + predot + ['*'] + postdot)


def _append_value (d, k, v):
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]


class Grammar (Language):

    def __init__ (self, rules=[], start_cat=None):
        if start_cat is None:
            start_cat = Category(rules[0].lhs.symbol)
        elif isinstance(start_cat, Symbol):
            start_cat = Category(start_cat)
        elif not isinstance(start_cat, Category):
            raise Exception('Start cat must be a Symbol or Category')

        self.rules = rules
        self._start_cat = start_cat
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
            self.rules[i] = Rule(lhs, rhs, r.cost)

    def _compute_terminals (self):
        terms = set()
        for r in self.rules:
            for x in r.rhs:
                if isinstance(x, Symbol):
                    terms.add(x)
        self._terminals = terms

    def start_cat (self):
        return self._start_cat

    def terminals (self):
        return self._terminals

    def nonterminals (self):
        return self._by_lhs.keys()

    def is_terminal (self, x):
        return x in self._terminals

    def is_nonterminal (self, x):
        return isinstance(x, Category) and x.symbol in self._by_lhs

    def expansions (self, cat):
        return self._by_lhs.get(cat.symbol, [])

    def continuations (self, cat):
        sym = cat if isinstance(cat, Symbol) else cat.symbol
        return self._by_rhs.get(sym, [])

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

    def is_left_derivable (self, Y, context):
        for Y1 in self.first(context):
            if Y & Y1:
                return Y1

    def is_reducible (self, Y, context):
        for r in self.continuations(Y):
            if self.is_left_derivable(r.lhs, context):
                return True

    def sample (self, *args, **kwargs):
        return Generator(self)(*args, **kwargs)

    def __str__ (self):
        return '\n'.join(repr(r) for r in self.rules)

    def __invert__ (self):
        return Parser(self)


class GrammarBuilder:

    def __init__ (self):
        self.rules = []
        self.start_cat = None

    def R (self, lhs, *rhs, cost=0):
        if isinstance(lhs, Symbol):
            lhs = Category(lhs)
        elif not isinstance(lhs, Category):
            raise Exception('Lhs is not a Category')
        self.rules.append(Rule(lhs, rhs, cost))
        if lhs.symbol.data == 'Start' and not lhs.features:
            self.start_cat = lhs

    def done (self):
        g = Grammar(self.rules, self.start_cat)
        self.rules = []
        return g

    def edit (self, grammar):
        self.rules = grammar.rules


class Parser:

    def __init__ (self, grammar):
        self._grammar = grammar

    def __call__ (self, sent, trace=False):
        self._chart = {}
        self._partial = {}
        self._todo = []
        self._best = None
        self._trace = trace
        for (i, w) in enumerate(string(sent)):
            self.shift(w, i)
            while self._todo:
                self.do_task()
        return self._best

    def shift (self, w, i):
        for r in self._grammar.continuations(w):
            self.add_node(r.shift(i))
        
    def add_node (self, node):
        key = (node.cat, node.i, node.j)
        if key in self._chart:
            oldnode = self._chart[key]
            if node.cost < oldnode.cost:
                self._chart[key] = node
                self.trace('Replace Node', node)
                self.eval_node(node)
            else:
                self.trace('Discard Alternative', X, node)
        else:
            self._chart[key] = node
            self.trace('Add Node', node)
            self.start(node)
            self.combine(node)
            self.eval_node(node)

    def start (self, node):
        for r in self._grammar.continuations(node.cat):
            m = r.start() * node
            if m:
                self.trace('Start', m)
                self.add_partial(m)

    def combine (self, node):
        for m in self._partial.get((node.i, node.cat.symbol), []):
            m1 = m * node
            if m1:
                self.trace('Combine', m, node, m1)
                self.add_partial(m1)
            else:
                self.trace('Unification Failure', m, node)

    def add_partial (self, m):
        if m.is_complete():
            heappush(self._todo, (m.j - m.i, id(m), m))
        else:
            key = (m.j, m.expectation().symbol)
            if key in self._partial:
                self._partial[key].append(m)
            else:
                self._partial[key] = [m]

    def do_task (self):
        (_, _, m) = heappop(self._todo)
        assert m.is_complete()
        self.add_node(m.reduce())

    def eval_node (self, node):
        if node.i == 0:
            best = self._best
            if (best is None or 
                node.j > best.j or
                node.j == best.j and node.cost < best.cost):
                self._best = node

    def trace (self, *args):
        if self._trace:
            print(args[0], *[repr(arg) for arg in args[1:]])


class Generator:

    def __init__ (self, grammar):
        self._grammar = grammar

    def __call__ (self, cat=None, max_attempts=100, max_depth=100, trace=False):
        if cat is None:
            cat = self._grammar.start_cat()
        for _ in range(max_attempts):
            try:
                self.pprint = PrettyPrinter()
                return self._generate_from(cat, 0, max_depth)
            except Exception as e:
                pass

    def _generate_from (self, cat, i, max_depth):
        print('cat=', cat)
        g = self._grammar
        rules = self._grammar.expansions(cat)
        

        print('rules=', rules)
        r = random.choice(rules)
        if r.is_preterminal():
            print('return', r.lhs, r.rhs)
            return Node(r.lhs, r.rhs, r, i, i+1, r.cost)
        else:
            m = r.topdown(cat)
            while not m.is_complete():
                chcat = m.expectation()
                if max_depth < 1:
                    raise Exception('Exceeded max_depth')
                j = m.j if m.children else i
                child = self._generate_from(chcat, j, max_depth-1)
                m = m * child
            return m.reduce()
