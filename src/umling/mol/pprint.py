
import sys, io


class PPrintIndent (object):

    def __init__ (self, pprinter, n):
        self.pprinter = pprinter
        self.n = n

    def __enter__ (self):
        self.pprinter._indent += self.n

    def __exit__ (self, t, v, tb):
        self.pprinter._indent -= self.n
        

class PPrintColor (object):

    def __init__ (self, pprinter, color):
        self.pprinter = pprinter
        self.color = color
        self.prevcolor = None

    def _set_color (self, color):
        self.pprinter._color = color
        sys.stdout.write(fg[color])
        sys.stdout.flush()

    def __enter__ (self):
        self.prevcolor = self.pprinter._color or 'default'
        self._set_color(self.color)

    def __exit__ (self, t, v, tb):
        self._set_color(self.prevcolor)


class PrettyPrinter (object):

    def __init__ (self, file=None):
        self._color = None
        self._indent = 0
        self._atbol = True
        self._brflag = False
        self._file = file
    
    def __enter__ (self):
        return self

    def __exit__ (self, t, v, tb):
        pass

    def __repr__ (self):
        return '<PPrinter %s>' % repr(self._file)

    def file (self):
        if self._file is None: return sys.stdout
        else: return self._file

    def indent (self, n=2):
        return PPrintIndent(self, n)

    def start_indent (self, n=2):
        self._indent += n
    
    def end_indent (self, n=2):
        self._indent -= n
        if self._indent < 0: self._indent = 0
    
    def br (self):
        self._brflag = True

    def color (self, c):
        return PPrintColor(self, c)

    def __call__ (self, *args, end=None, color=None):
        if color is None:
            self._call1(args, end)
        else:
            with self.color(color):
                self._call1(args, end)
                
    def _call1 (self, args, end):
        if end is None:
            end = '\n'
        first = True
        for arg in args:
            if first: first = False
            else: self.file().write(' ')
            self.write(str(arg))
        if end:
            self.write(str(end))

    def write (self, s):
        f = self.file()
        i = 0
        n = len(s)
        while i < n:
            j = s.find('\n', i)
            if j < 0: j = n
            # it is possible that s[0] == '\n'
            if i < j:
                if self._brflag and not self._atbol:
                    f.write('\n')
                    self._atbol = True
                if self._atbol:
                    f.write(' ' * self._indent)
                f.write(s[i:j].replace('\x1b', '\\x1b'))
                self._atbol = False
            # if j < n then s[j] == '\n'
            if j < n:
                f.write('\n')
                j += 1
                self._atbol = True
            i = j
    
    def freshline (self):
        if not self._atbol:
            self.write('\n')

    def now (self, *args, end=''):
        self.__call__(*args, end)
        self.file().flush()
    
    def flush (self):
        self.file().flush()


class PrettyString (PrettyPrinter):

    def __init__ (self):
        PrettyPrinter.__init__(self, io.StringIO())

    def __str__ (self):
        return self._file.getvalue()
