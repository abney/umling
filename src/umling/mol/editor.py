
from .lang import FSABuilder, Language
from .grammar import GrammarBuilder


class Editor:

    def __init__ (self):
        self.target = None

    def check_edit_fsa (self):
        if self.target is None:
            self.target = FSABuilder()
        elif not isinstance(self.target, FSABuilder):
            raise Exception('Currently editing something else; call erase first')

    def check_edit_grammar (self):
        if self.target is None:
            self.target = GrammarBuilder()
        elif not isinstance(self.target, GrammarBuilder):
            raise Exception('Currently editing something else; call erase first')

    def E (self, *args):
        self.check_edit_fsa()
        self.target.E(*args)

    def F (self, *args):
        self.check_edit_fsa()
        self.target.F(*args)

    def R (self, *args):
        self.check_edit_grammar()
        self.target.R(*args)

    def done (self):
        if self.target is None:
            raise Exception('Not building anything')
        out = self.target.done()
        self.target = None
        return out

    def erase (self):
        self.target = None

    def edit (self, x):
        if isinstance(x, Language):
            self.check_edit_fsa()
            self.target.edit(x)


#--  Globals  ------------------------------------------------------------------

_editor = Editor()
E = _editor.E
F = _editor.F
R = _editor.R
done = _editor.done
erase = _editor.erase
edit = _editor.edit
