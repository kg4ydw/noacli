
# These two classes attempt to cover up the differences betwen
# python's native I/O classes and Qt's portable I/O classes, covering
# the common functionality they both have.
#
# This would have inherited from either class, but neither support a
# constructor that would allow initializing with an existing device.
#
# In particular, these implement methods needed to insure asyncrhonous
# I/O will neither block, run into a premature end of file, or run
# past EOF when there will be no more data, and the resulting types
# pass the duck type test so they can be used with native python classes.


import sys
import os
import io

from PyQt5.QtCore import  QIODevice, QSocketNotifier, QProcess

# can't monkeypatch QProcess, so wrapping it instead
class betterQProcess():
    '''This pretends a QIODevice is a BufferedReader by implementing the
        bare minimum needed here.  Note that both types include all
        the same functionality, but with different function names and
        return types.
    '''
    def __init__(self, qio):
        self.qio = qio
    def strpeek(self, size):
        return str(self.qio.peek(size),'utf-8')
    def __iter__(self):
        return self
    def __next__(self):
        return str(self.qio.readLine(), 'utf-8')
    ## try to dynamicaly patch in anything else
    def __getattr__(self, name):
        f=getattr(self.qio,name) # next time get it direct
        setattr(self,name,f)
        return f

        
## missing stuff from TextIOWrapper
class betterTextIOWrapper():
    def __init__(self, tiow):
        self.tiow = tiow
    def strpeek(self, size):  # XX not gonna fake size default
        return self.tiow.buffer.peek(size).decode('utf-8')
    def canReadLine(self):
        return '\n' in self.strpeek(1024)

    # can't copy these, they have to really exist
    def __iter__(self): return self.tiow.__iter__()
    def __next__(self): return self.tiow.__next__()
    # and bring in anything else we need on demand
    def __getattr__(self, name):
        f=getattr(self.tiow, name) # next time get it direct
        setattr(self, name, f)
        return f
