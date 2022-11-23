import os
from enum import Enum


# This is a very primitive command parser, but it should be sufficent for the
# kinds of things this shell needs.

# Note that this explicitly doesn't handle quotes or backslashes and
# doesn't do much with spaces.  As is, it can pass arguments to
# commands with spaces in them.  If this worked harder on spaces, it
# would have to also add quoting to support filenames with spacse.

# will use the names of these for the pull down menu
class OutWin(Enum):
    Default = 0  # use current default or command default
    Small = 1
    "Send output to the small output dock window"
    QTail = 2
    Tail = 2 # alias
    "View possibly growing output in a scrollable browser"
    Log = 3
    "Merge output from this and other commands into the merged log dock window"

builtinCommands = {
 #### output destinations
 # 'name' : functor  --> functor(rest)
    'log' : OutWin.Log,
    'tail': OutWin.QTail,
    'qtail': OutWin.QTail,
    'small': OutWin.Small, # default
    #'table': XXX not implemented yet!
    ## actual commands will be added by @builtin('command')
}

class commandParser:
    # decorator generator to register commands
    # maybe use __doc__ strings as help strings eventually
    def builtin(name):
        def decorator(func):
            builtinCommands[name] = func
            return func
        return decorator
    # wrappers are user editable and pre-parsed
    # The entire user command is sent to the wrapper via execv as is.
    # Output from a wrapper can default to a specific output target (above)
    # but can be directed to a different one by the user.
    # Except for the first manditory wrapper, these wrappers are examples.
    wrappers = { # SETTING
        # 'name' : [ target, args... ],
        'bash': [ OutWin.Small, 'bash', '-c'],
        'sh': [ OutWin.Small, 'bash', '-c'],
        # ssh needs a parameter, so the user can add it themselves
        # ssh presumes you have login w/o password working (via keys or multiplexing)
        # 'hostname': [ OutWin.small, 'ssh', 'hostname'],
        'xterm': [ OutWin.Log, 'xterm', '-e' ],
        # gnome terminal doesn't work as well, it needs help
        'gterm': [ OutWin.Log , 'gnome-terminal', '--', 'bash', '-c'],
        }
    def __init__(self):
        self.defaultWrapper = 'bash' #  SETTING
        self.defaultOutWin = OutWin.Small # SETTING
        
    def parseCommand(self, cmd):
        # returns one of
        #  [title, outwin, args] 
        #  None if the command was handled internally
        #  string: command was handled internally and generated output
        # if command can't be parsed, just use the default wrapper
        # exception: something went wrong
        cmd = cmd.strip()
        outwin = OutWin.Default
        title = None
        if cmd[0]=='#':  # strip out the first line but keep for title
            (title, sep, rest) = cmd[1:].strip().partition('\n')
            cmd = rest
        while cmd:
            sa = cmd.split(None,1)
            word = sa[0]
            if len(sa)>1:
                rest=sa[1]
            else:
                rest=''
            if word in builtinCommands:
                func = builtinCommands[word]
                if type(func) is OutWin:
                    #print('window type word={} rest=({})'.format(word,rest)) # DEBUG
                    outwin = func
                    cmd = rest
                    continue
                return func(self, title, outwin, rest)  # most of these return None
            if self.defaultWrapper not in self.wrappers:
                self.defaultWrapper='bash'
                if self.defaultWrapper not in self.wrappers:
                    # put it back!!
                    self.wrappers['bash'] = [OutWin.Small, 'bash', '-c']
            if word not in self.wrappers:
                # put it all back the way it was
                word = self.defaultWrapper
                rest = cmd
                # fall through as if default wrapper was specified
            # print('word={} rest=({})'.format(word,rest)) # DEBUG
            if word in self.wrappers:
                if not title:
                    title = rest[:30].strip() # SETTING
                if outwin==OutWin.Default:
                    outwin = self.wrappers[word][0]
                return [title, outwin, self.wrappers[word][1:] + [rest]]
            print('iloop: This cant happen') # DEBUG
            # can't get here
        print('oloop This cant happen') # DEBUG
        # can't get here

    @builtin('cd')
    @builtin('chdir')
    def cmd_chdir(self, title, outwin, rest):
        '''Change to a new working directory'''
        # This doesn't do any parsing, so you can have dirnames with
        # spaces in them without needing to support quoting.
        if len(rest)==0:  # no arg takes you home
            rest = os.environ.get('HOME') 
        try:
            os.chdir(rest)
        except OSError as e:
            return e.strerror
        return os.getcwd()
    
    @builtin('setwrap')
    def cmd_setwrap(self, title, outwin, rest):
        '''Change to a new default command wrapper'''
        if rest in self.wrappers:
            self.defaultWrapper = rest
        else:
            return "Wrapper '{}' not found.".format(rest)
        return None
    @builtin('direct')
    def cmd_direct(self, title, outwin, rest):
        '''Run an executable with arguments directly instead of sending it to a wrapper for parsing and execution'''
        # very simple parsing, hope there's no quotes in this
        return [title, outwin]+ [rest.split()]
    @builtin('help')
    def cmd_help(self, title, outwin, rest):
        '''Describe or list built in commands.'''
        words = rest.split()
        if len(words)<1:
            return "Built in commands: "+(" ".join(sorted(builtinCommands.keys())))
        text = ''
        for word in words:
            if word in builtinCommands:
                if hasattr(builtinCommands[word],'__doc__'):
                    text += "{}: {}\n\n".format(word, builtinCommands[word].__doc__)
                else:
                    text += "{}: no documentation\n\n".format(word)
            else:
                text += "{} not found\n\n".format(word)
        return text

    #### Other future built-in commands not implemented yet
    # 'pwd':  is this needed at all?  external pwd works fine
    # 'pushd':'popd': needs internal directory stack and probable parsing
    #  setenv -- bash or csh syntax? and this is already in GUI
    #  qtail like command to open multiple files for viewing at once
        
        
