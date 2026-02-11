
from .pip import Expr

tokens = ('NAME', 'EMPTYSET')

literals = ('[', ']', '(', ',', ')', '=', '&', '$', ':', '|', '_', '{', '}', '@')

t_NAME = r'[a-zA-Z_][a-zA-Z0-9_]*'
t_EMPTYSET = r'{}'
t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

from .ply import lex
lexer = lex.lex()

precedence = (
    ('left', ':'),
    ('left', '&')
)

def p_expr_equality (p):
    "expr : term '=' term"
    p[0] = Expr('=', p[1], p[3])

def p_expr_conjunction (p):
    "expr : expr '&' expr"
    p[0] = Expr('&', p[1], p[3])

def p_expr_label (p):
    "expr : '@' NAME"
    p[0] = Expr('@', p[2])

def p_expr_labeldef (p):
    "expr : '@' NAME ':' expr"
    p[0] = Expr(':', p[2], p[4])

def p_expr_presupposition (p):
    "expr : expr '|' expr"
    p[0] = Expr('|', p[1], p[3])

def p_term_name (p):
    "term : NAME"
    p[0] = Expr('V', p[1])

def p_term_localvar (p):
    "term : '[' NAME ']'"
    p[0] = Expr('[]', p[2])

def p_term_emptyset (p):
    "term : EMPTYSET"
    p[0] = Expr('0')
    
def p_term_summation (p):
    "term : '$' NAME expr"
    p[0] = Expr('$', p[2], p[3])

def p_expr_predapp (p):
    "expr : NAME '(' termlist ')'"
    p[0] = Expr('A', p[1], p[3])

def p_termlist_start (p):
    "termlist : "
    p[0] = []

def p_termlist_continue (p):
    "termlist : termlist term"
    p[0] = p1 + [p[2]]

def p_error (p):
    if p:
        print("Syntax error at '%s'" % p.value)
    else:
        print("Syntax error at EOF")

from .ply import yacc
parser = yacc.yacc()

def parse (s):
    return yacc.parse(s)
