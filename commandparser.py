
__license__   = 'GPL v3'
__copyright__ = '2022, Steven Dick <kg4ydw@gmail.com>'

# Command parser and implementation for internal commands

import os
import sys
from enum import Enum
from PyQt5.Qt import pyqtSignal
from PyQt5.QtCore import QSettings, QT_VERSION_STR, PYQT_VERSION_STR

# This is a very primitive command parser, but it should be sufficent for the
# kinds of things this shell needs.

# Note that this explicitly doesn't handle quotes or backslashes and
# doesn't do much with spaces.  As is, it can pass arguments to
# commands with spaces in them.  If this worked harder on spaces, it
# would have to also add quoting to support filenames with spaces.
#
# This tries to pass commands to the wrapper shell as unmolested as possible.
# This reduces needing multiple layers of quoting to get things through.

# will use the names of these for the pull down menu
class OutWin(Enum):
    Default = 0  # use current default or command default
    Small = 1
    QTail = 2
    Tail = 2 # alias
    Log = 3
    Table = 4
    Internal = 99  # only use internally as a status

# enums don't natively support doc strings; this is used by cmd_help
OutWin.Small.__doc__ = "Send output to the small output dock window"
OutWin.QTail.__doc__ = "View possibly growing output in a scrollable browser"
OutWin.Log.__doc__ = "Merge output from this and other commands into the merged log dock window"
OutWin.Table.__doc__="Parse file output as a table (delimiters autodetected)"

builtinCommands = {
 #### output destinations
 # 'name' : functor  --> functor(rest)
    'log' : OutWin.Log,
    'tail': OutWin.QTail,
    'qtail': OutWin.QTail,
    'small': OutWin.Small, # default
    'table': OutWin.Table,
    ## actual commands will be added by @builtin('command')
}

class commandParser:
    new_default_wrapper = None # non-Qt fake signal (unfancy, but we only need one)
    # decorator generator to register commands
    # use __doc__ strings as help strings
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
    wrappers = {
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
        # get default shell and make it the default wrapper
        shell = os.environ.get('SHELL')
        base = os.path.basename(shell)
        basem, ext = os.path.splitext(base)  # windows??
        # this intentionally bypasses setwrap so it doesn't get saved
        if basem not in self.wrappers: # don't override if it exists already
            # This assumes '$SHELL -c' works for $SHELL
            self.wrappers[basem] = [ OutWin.Small, shell, '-c' ]
        self.defaultWrapper = basem  # SETTING ?
        self.applySettings() # but this can override

    # Should this be called with sync settings?
    def applySettings(self):
        qs = QSettings()
        qs.beginGroup('Wrappers')
        for key in qs.childKeys():
            # probably unnecessary sanity checks
            v = qs.value(key,None)
            if not v or len(v)<2: continue
            if type(v[0])!=OutWin: continue
            # not gonna verify the rest
            self.wrappers[key] = v
        
    def parseCommand(self, cmd):
        # returns one of
        #  [title, outwin, args] 
        #  [title, outwin, [outwinargs], args] 
        #  [title, outwin, ['--files' or '--file', outwinargs], [filenames] ] 
        #  None if the command was handled internally
        #  string: command was handled internally and generated output
        # if command can't be parsed, just use the default wrapper
        # exception: something went wrong
        cmd = cmd.strip()
        outwin = OutWin.Default
        gotoutwin = False
        title = None
        outwinArgs = None
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
            # handle built in commands, but not two OutWin in a row
            if word in builtinCommands and not (gotoutwin and type(builtinCommands[word])==OutWin):
                func = builtinCommands[word]
                if type(func) is OutWin:
                    #print('window type word={} rest=({})'.format(word,rest)) # DEBUG
                    outwin = func
                    cmd = rest
                    gotoutwin = True
                    # table and tail can take parameters
                    if outwin in [OutWin.QTail, OutWin.Table] and cmd[0]=='-':
                        outwinArgs=[]
                        while len(cmd)>0 and cmd[0]=='-':
                            # dumb arg parser, all args must be -something or -something=something
                            sa = cmd.split(None,1)
                            outwinArgs.append(sa[0])
                            if len(sa)>1:
                                cmd=sa[1]
                            else:
                                cmd=''
                        if '--file' in outwinArgs:
                            return [title, outwin, outwinArgs, cmd]
                        elif '--files' in outwinArgs:
                            return [title, outwin, outwinArgs, cmd.split()]
                    continue
                #print('func='+str(func)) # DEBUG
                return func(self, title, outwin, rest)
            # must be an external command
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
            #print('word={} rest=({})'.format(word,rest)) # DEBUG
            if word in self.wrappers: # should always be true
                if not title:
                    title = rest[:30].strip() # SETTING
                if outwin==OutWin.Default:
                    outwin = self.wrappers[word][0]
                if outwinArgs:
                    return [title, outwin, outwinArgs, self.wrappers[word][1:] + [rest]]
                else:
                    return [title, outwin, self.wrappers[word][1:] + [rest]]
            print('iloop: This cant happen') # EXCEPT
            # can't get here
        print('oloop This cant happen') # EXCEPT
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

    @builtin('setwrapper') # how do you spell this again?
    @builtin('setwrap')
    def cmd_setwrap(self, title, outwin, rest):
        '''Change to a new default command wrapper, or lists the current wrapper if none is supplied'''
        # NOTE: setwrap INTENTIONALLY does not save this as a setting!
        if rest=='':
            return 'Current default wrapper is set to '+self.defaultWrapper
        if rest in self.wrappers:
            self.defaultWrapper = rest
            if self.new_default_wrapper:  # fake signal
                self.new_default_wrapper(rest)
        else:
            return "Wrapper '{}' not found.".format(rest)
        return None
    @builtin('addwrap')
    def cmd_addwrap(self, title, outwin, rest):
        '''Add a wrapper shortcut to wrap unparsed commands'''
        words = rest.split()
        if len(words)<1:
          return 'addwrap: '+(' '.join(self.wrappers.keys()))
        elif len(words)==1:
          w = words[0]
          if w in self.wrappers:
            return ' '.join(['addwrap',w,'= (', self.wrappers[w][0].name,')']+ self.wrappers[w][1:])
          else:
            return 'addwrap {} not found'.format(w)
        self.wrappers[words[0]] = [outwin] + words[1:]
        # and save it
        qs = QSettings()
        qs.beginGroup('Wrappers')
        qs.setValue(words[0], self.wrappers[words[0]])
        return "Added wrap "+words[0]
    
    @builtin('unwrap')
    def cmd_unwrap(self, title, outwin, rest):
        '''Delete a wrapper'''
        # Note that built in wrappers will return on next start.
        rest = rest.strip()
        if rest=='':
            return "No wrapper specified for deletion."
        if rest==self.defaultWrapper:
            return "Can't delete default wrapper "+self.defaultWrapper
        if rest not in self.wrappers:
            return "Wrapper {} already deleted.".format(rest)
        try:
            del self.wrappers[rest]
        except:
            # This can't happen, but if it does, whatever.
            pass
        qs = QSettings()
        qs.beginGroup('Wrappers')
        qs.remove(rest)
        qs.endGroup()
        return "Wrapper {} removed.".format(rest)

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
                    text += "{}: {}\n".format(word, builtinCommands[word].__doc__)
                else:
                    text += "{}: no documentation\n".format(word)
            else:
                text += "{} not found\n".format(word)
        return text


    @builtin('version')
    def cmd_version(self, title, outwin, rest):
        '''What version is am I?'''
        from noacli import __version__
        return 'Versions: noacli '+__version__ +', Qt '+ QT_VERSION_STR + ', PyQt '+ PYQT_VERSION_STR+ ', Python '+sys.version

    @builtin('type')
    def cmd_type(self, title, outwin, rest):
        '''Find what things match the given command'''
        t=''
        words=rest.split()
        # XXX this should get the path from the propagated environment
        # but only the real one is available here, hope the user didn't change it
        pathdirs = os.get_exec_path()
        for cmd in words:
            t+= cmd+':\n'
            # check internal command dictionary
            if cmd in builtinCommands:
                t += '  built in command\n'
            # check wrappers
            if cmd in self.wrappers:
                t += '  wrapper: '+(' '.join(['(', self.wrappers[cmd][0].name,')']+ self.wrappers[cmd][1:]))+"\n"
            if cmd[0]=='/': continue # XX ignore full path commands for now
            # check external paths
            for dir in pathdirs:
                prefix='  '
                f = os.path.join(dir,cmd)
                if os.path.islink(f):
                    try:
                        # rf = os.path.realpath(f, strict=True) # maybe not
                        rf = os.path.realpath(f)
                        if not os.path.exists(rf):
                            t += prefix + f + ' BROKEN symlink to '+rf+'\n'
                        else:
                            t += prefix + f + ' ==> '+ rf +'\n'
                    except OSError:
                        t += prefix + f + ' BROKEN symlink\n'
                        continue
                    except Exception as e:
                        t += prefix + f + ' broken\n'
                        print('realpath: '+str(e)) # EXCEPT
                        continue
                elif os.path.isfile(f):
                    t += prefix + f +'\n'
                # else: don't say anything if it isn't found in this dir

        return t
            
    #### Other future built-in commands not implemented yet
    # 'pwd':  is this needed at all?  external pwd works fine
    # 'pushd':'popd': needs internal directory stack and probable parsing
    #  setenv -- bash or csh syntax? and this is already in GUI
    #  qtail like command to open multiple files for viewing at once
        
        
