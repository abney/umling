

class ExprType:

    def __init__ (self, name, sig=''):
        self._name = name
        self._signature = sig


class Expr:

    def __init__ (self, etype, *args):
        self._etype = etype
        self._args = args

    def __getitem__ (self, i):
        if i == 0:
            return self._etype
        else:
            return self._args[i-1]

    def __len__ (self):
        return len(self._args) + 1

    def __iter__ (self):
        yield self._etype
        yield from self._args


ExprTypes = {
    'V': ExprType('Variable', 'S'),
    '[]': ExprType('LocalVariable', 'S'),
    '@': ExprType('FormulaLabel', 'S'),
    '0': ExprType('EmptySet'),
    'A': ExprType('PredicateApplication', '(*)'),
    '(': ExprType('StartList', ''),
    ')': ExprType('EndList', ''),
    '=': ExprType('Equality', 'EE'),
    '&': ExprType('Conjunction', 'EE'),
    '$': ExprType('Summation', 'EE'),
    ':': ExprType('FormulaLabelDefinition', 'EE'),
    '|': ExprType('Presupposition', 'EE')
}


