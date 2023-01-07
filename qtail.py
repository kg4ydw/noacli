#!/usr/bin/env python3

__license__   = 'GPL v3'
__copyright__ = '2022, Steven Dick <kg4ydw@gmail.com>'

# qtail: think of this as a graphical version of less
#
# Given a big blob of text, dump it in a window with a scrollbar.
# Handle files that grow, stdin, and integration with noacli
#
# Tries to not run out of memory by only keeping 10k lines by default.

## Bugs:
# Doesn't handle backscrolling beyond its internal buffers
# Currently doesn't chunk input well which causes delays and hangups

import os, re, sys, time, argparse, copy, math
from functools import partial
from math import ceil

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor, QFont, QTextDocument
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QLineEdit, QActionGroup, QWidgetAction, QSpinBox, QAbstractSpinBox, QShortcut
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QSocketNotifier, QSize, QTimer, QProcess
from PyQt5.Qt import Qt, pyqtSignal

from lib.qtail_ui import Ui_QtTail
from lib.typedqsettings import typedQSettings
from lib.buildsearch import buildSearch

typedQSettings().registerOptions({
    'QTailMaxLines': [ 10000, 'maximum lines remembered in a qtail window', int],
    'QTailReadBlock':[8192, 'Maximum block size to read at once (higher for more performance but lower responsiveness)', int],
    'QTailEndBytes': [ 1024*1024, 'Number of bytes qtail rewinds a file', int],
    'QTailDefaultTitle': [ 'subprocess', 'Default title for a qtail process window', str ],
    'QTailDelayResize':[ 3, 'Resize qtail to fit output again seconds after first input arrives', int],
    'QTailPrimaryFont': [None, 'Default font for qtail', QFont],
    'QTailSecondaryFont': [None, 'Alternate font for qtail', QFont],
   #'QTailFormat': [ 'plaintext', 'plaintext or html', str ],
   #'QTailFollow': [ False, 'scroll qtail to the end of the file on updates', bool ],
   #'QTailWrap':  [ True, 'wrap long lines', bool ]
   #'QTailSearchMode': ['exact', 'exact or regex search mode', str],
   #'QTailCaseInsensitive': [True, 'Ignore case when searching', bool],
    'QTailWatchInterval': [30, "Default automatic refresh interval for qtail in watch mode", int],
})    

class softArgumentParser(argparse.ArgumentParser):
    exit_on_error=True
    def exit(self, status=0, message=None):
        if self.exit_on_error:
            super().exit(status,message)
        elif status:
            print(message) # EXCEPT
            raise Exception(message) # XXX need to test error handling
        #else: print('status={} message={}'.format(status,message)) #DEBUG

# options values -- set defaults
class myOptions():
    def __init__(self):
        self.maxLines = 10000
        self.tailFrag = 1000*1000
        # note: maxLines*80 is close to tailFrag
        self.isCommand = False
        self.file = False
        self.whole = False
        self.title = None
        self.format = None # p=PlainText m=Markdown h=Html
        self.url = False
        # XX whole file mode vs tail mode?  oneshot vs. follow?
        # XX alternate format options: html markdown fixed-font

    def processOptions(self, app, args=None):
        # vestiges of QCommandLineParser remain here (maybe refactor later)
        parser = softArgumentParser(prog='qtail', description='View and follow the tail of a file or pipe')
        #XX parser.add_argument("--command",help="view output from command", action='store_true')

        ## copy some options from tail, but not exactly
        parser.add_argument('-c', '--bytes', type=int, metavar='bytes', help='maximum size of tail chunk in bytes', dest='tailFrag', default=self.tailFrag)
        parser.add_argument('-n', '--lines', help='keep the last NUM lines', metavar='NUM', type=int, default=self.maxLines)
        parser.add_argument('-w','--whole', help='look at the whole file, not just the tail', action='store_true')
        parser.add_argument('-t','--title', help='set window title if a filename is not supplied',metavar='title')
        parser.add_argument('--format', help='Pick a format (plaintext, html)', choices=['plaintext','html', 'markdown','p','h','m'], metavar='format', default='plaintext') # XX markdown doesn't work
        parser.add_argument('--url', help='Read input from a url or filename and autodetect format', action='store_true')
        parser.add_argument('--nowrap', help="Disable word wrap by default", action='store_true') # set in start()
        parser.add_argument('--autorefresh', '--auto', nargs='?', type=int, metavar='seconds', const=0, help='Enable autorefresh and (optionally) set refresh interval')

        parser.add_argument('filename', nargs=argparse.REMAINDER)
        
        #XX more options from original tail
        # -f  : currently default always on
        # --retry
        # --max-unchanged-status (a timeout would be better)
        # --pid
        # -s --sleep  (for stat and pid polling)
        ## other possible options
        # --timeout-unchanged (reopen or quit on timeout)
        # --timeout-reopen
        # --timeout-quit  (for pid and unchanged)
        # --timeout-countdown (starts countdown before quitting)
        # --triansient (exit immediately on pid, unchanged)
        if args:
            # called from noacli
            parser.exit_on_error = False
            # let the caller catch exceptions
            (args, rest) = parser.parse_known_args(args)
            # keep the rest just in case
            self.rest = rest
        else:
            args = parser.parse_args()
        self.argparse = args

        ## this might be called late, so apply settings as we go
        # XX future: refactor to use self namespace and do less checking
        # self.isCommand = parser.command # XX not implemented yet
        if args.tailFrag > 100: self.tailFrag = args.tailFrag
        self.maxLines = args.lines
        self.whole = args.whole
        if self.whole: self.maxLines = 0
        if args.title: self.title=args.title # XX late apply?
        if args.format:
            if args.format=='html': self.format='h'
            elif args.format=='markdown': self.format='m' # XX
            else: self.format=None
        if args.url: self.url = True

        self.args = args.filename
        return self.args
                
class QtTail(QtWidgets.QMainWindow):
    window_close_signal = pyqtSignal()
    want_resize = pyqtSignal()
    want_read_more = pyqtSignal(str)
    def __init__(self, options=None, parent=None):
        super().__init__()
        self.runcount = 0
        self.timestart = time.monotonic() # in case we miss the real start
        self.runtime = None
        self.disableAdjustSize = False
        self.eof = 0 # hack
        self.buttonCon = None
        dir = os.path.dirname(os.path.realpath(__file__))
        icon = QtGui.QIcon(os.path.join(dir,'icons', 'qtail.png'))
        if icon.isNull() or len(icon.availableSizes())<1: # try again
            icon = QtGui.QIcon('qtail.png')
        self.setWindowIcon(icon)

        # connect to my own event so I can send myself a delayed signal
        self.want_resize.connect(self.actionAdjust, Qt.QueuedConnection) # delay this
        self.want_read_more.connect(self.readtext, Qt.QueuedConnection) # read more after everything else is updated

        if options==None:
            options=myOptions()
        else:
            options = copy.copy(options) # don't modify parent object
        
        self.firstRead = True
        self.resizecount = 0
        self.opt = options
        self.ui = Ui_QtTail()
        self.ui.setupUi(self)
        self.textbody = self.ui.textBrowser
        if self.opt.maxLines>0:
            self.textbody.document().setMaximumBlockCount(self.opt.maxLines)

        ## build the Mode menu because QtDesigner can't do it
        m = self.ui.menuMode

        line = QSpinBox(m)  # or double?
        line.setMaximum(86400)
        line.setSingleStep(10)  # redundant with adaptive on
        line.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        line.setWrapping(False) # stick at ends of range
        line.setValue(typedQSettings().value('QTailWatchInterval',30))
        line.setToolTip('Refresh interval')
        line.editingFinished.connect(self.setWatchInterval)
        line.setSuffix(' seconds')
        self.ui.intervalLine = line
        wa = QWidgetAction(m)
        wa.setDefaultWidget(line)
        m.addAction(wa)
        ### can't do this yet
        #if type(self.file)!=QProcess: # can't watch a non-process
        #    self.ui.actionWatch.setEnabled(False) 
        self.timer = QTimer()
        self.timer.timeout.connect(self.reloadOrRerun)
        # note: this intentionally doesn't refresh on settings change
        self.reinterval = typedQSettings().value('QTailWatchInterval',20)
        # find
        self.editorShortcut = QShortcut(QtGui.QKeySequence('ctrl+f'), self)
        self.editorShortcut.activated.connect(self.ui.searchTerm.setFocus)

        m = self.ui.menuView
        primary = self.getFontSetting('QTailPrimaryFont')
        if primary:
            m.addAction(primary.toString(),partial(self.ui.textBrowser.document().setDefaultFont, primary))
            # and actually use it now
            self.ui.textBrowser.document().setDefaultFont(primary)
        secondary = self.getFontSetting('QTailSecondaryFont')
        if secondary:
            m.addAction(secondary.toString(),partial(self.ui.textBrowser.document().setDefaultFont, secondary))
        try:
            # hide functionality broken in Qt 5.12 XX (delete this later)
            v = QtCore. QT_VERSION_STR.split('.')
            if v[0]=='5' and int(v[1])<13:
                print("Disabling regex, sorry.")
                self.ui.actionUseRegEx.setChecked(False)
                self.ui.actionUseRegEx.setVisible(False)
                self.ui.actionUnicode.setVisible(False)
        except:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resizecount += 1
        # don't autoresize if the user resized, ignore first resize
        if self.resizecount>1:
            self.firstRead = False

    def getFontSetting(self, name):
        font = typedQSettings().value(name, None)
        if font and font.family():
            return font
        else:
            return None

    def setButtonMode(self):
        if hasattr(self,'file') and type(self.file)==QProcess:
            if self.file.state()!=QProcess.NotRunning:
                self.rebutton('Kill', self.terminateProcess)
            elif self.ui.actionWatch.isChecked():
                self.rebutton('Rerun', self.reloadOrRerun)
            else:
                self.rebutton('Close', self.close,'modeNorun')
        else: 
            ## XX distinguish between stdin and a file eventually (seekable?)
            # print(type(self.file), self.filename, hasattr(self, 'filename')) # DEBUG
            if hasattr(self,'filename') and self.ui.actionWatch.isChecked():
                self.rebutton('Reload',self.reload)
            else:
                self.rebutton('Close', self.close,'modefile')
        #else: # file
        
    def tweakInterval(self):
        if not hasattr(self, 'reinterval'): self.reinterval=30
        if self.reinterval<1: self.reinterval=1
        if self.runcount < 3: return
        dutycycle = 0.5
        if self.reinterval<10 and self.runtime<10:
            dutycycle = 0.1 # lower duty cycle for high freq
        mininterval = self.runtime / dutycycle
        if self.reinterval < mininterval:
            self.reinterval = mininterval
            msg = "Resetting timer to {:1.3f}s (runtime={:1.3f}s)".format(self.reinterval, self.runtime)
            if typedQSettings().value('DEBUG',False): print(msg) # reset interval
            self.statusBar().showMessage(msg, math.floor(mininterval*10))
            self.actionAutoRefresh()
            self.ui.intervalLine.setValue(math.floor(mininterval+0.5))
        if self.reinterval == 1:
            self.ui.intervalLine.setSuffix(' second')
        else:
            self.ui.intervalLine.setSuffix(' seconds')
        # XX if duty cycle > 50% turn off timer if window is obscured
        # is there an event when window is obscured??
        
    def setWatchInterval(self, value=None):
        if value:
            val = value
            self.ui.intervalLine.setValue(value)
        else:
            val = self.ui.intervalLine.value()
        self.reinterval = val
        self.tweakInterval()
        self.actionAutoRefresh() # set timer
            
    def actionAutoRefresh(self):
        checked = self.ui.actionAutorefresh.isChecked()
        if checked:
            self.timer.start(math.floor(self.reinterval*1000+0.5))
        else:
            self.timer.stop()
            
    def reloadOrRerun(self):
        # XX reset and restart timer if this was user triggered?
        self.firstRead = False  # don't trigger resize if button pushed
        # XXX on reload maybe cancel resize timer too?
        if type(self.file)==QProcess:
            #print("proc state="+str(self.file.state())) # DEBUG
            if self.file.state()==QProcess.Running:  # it's taking a long time
                return
            else:
                self.ui.textBrowser.clear()
                if typedQSettings().value('DEBUG',False): print('rerun '+(" ".join(self.file.arguments()))) # DEBUG
                self.file.start()  # XXX does this work? reactivate data stream?
        else:
            self.reload()
            
    def closeEvent(self,event):
        self.timer.stop()  # restart this on reopen?
        self.window_close_signal.emit()
        super().closeEvent(event)

    def show(self): # restart timer
        super().show()
        # restart timer if it is active
        self.actionAutoRefresh()

    @QtCore.pyqtSlot()
    def clearFinds(self):
        self.textbody.setExtraSelections([])
        
    @QtCore.pyqtSlot(str)
    def simpleFind(self, text):
        start = self.textbody.textCursor()
        # remember previous find
        if start.hasSelection():
            ess = self.textbody.extraSelections()
            e=None
            for e in ess:
                if e.cursor.anchor()==start.anchor():
                    break
            if e and e.cursor.anchor()==start.anchor():
                e.cursor = start  # in case selection changed
            else: # make a new one
                es = QTextEdit.ExtraSelection()
                es.format.setBackground(QtGui.QBrush(Qt.yellow)) # SETTING
                es.cursor = start
                ess.append(es)
                self.textbody.setExtraSelections(ess)
        searchterm = buildSearch(text, self.ui)
        findflags = QTextDocument.FindFlags()
        if not self.ui.actionCaseInsensitive.isChecked():
            findflags |= QTextDocument.FindCaseSensitively
        if self.ui.actionWholeWords.isChecked():
            findflags |= QTextDocument.FindWholeWords
        # XX FindBackward
        if searchterm:
            success = self.textbody.find(searchterm, findflags)
        else:
            # XXX warn error
            return
        if success:
            self.findcount += 1
            es = self.textbody.extraSelections()
            self.statusBar().showMessage('Found {}/{}'.format(self.findcount, len(es)))
        else:
            # try again
            cursor = self.textbody.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            self.textbody.setTextCursor(cursor)
            success = self.textbody.find(searchterm, findflags)
            if success:
                if self.findcount:
                    m = 'Wrapped after {}/{}'.format(self.findcount,len(self.textbody.extraSelections()))
                    es = self.textbody.extraSelections()
                    cs = sorted([e.cursor for e in es])
                    ## XXX would a list of findings be useful to show?
                    #for e in cs:
                    #    print("{}: {}".format(e.position(), e.selectedText())) # DEBUG
                else:
                    m = 'Wrapped'
                self.statusBar().showMessage(m)
                self.findcount = 1;
            else:
                self.textbody.setTextCursor(start)
                self.statusBar().showMessage('Not found')

    @QtCore.pyqtSlot(str)
    def simpleFindNew(self, text):
        self.findcount = 0
        self.simpleFind(text)

    @QtCore.pyqtSlot()
    def simpleFind2(self):
        self.simpleFind(self.ui.searchTerm.text())

    @QtCore.pyqtSlot()
    def readtext(self, fromwhere='unk'):
        blocksize = typedQSettings().value('QTailReadBlock',1024)
        b = self.file.read(blocksize)
        # b = None?  b=0? b<blocksize?  b==blocksize?
        #print(type(b),len(b), self.file.atEnd()) # DEBUG
        e = self.textbody.textCursor()
        e.movePosition(QtGui.QTextCursor.End)
        #print('read {}: {}'.format(fromwhere,len(b))) # DEBUG
        if b==None: # already got EOF (probably?)
            #if typedQSettings().value('DEBUG',False):print("EOF from "+fromwhere)
            self.eof = 6
        if b==None or len(b)==0:  # EOF hack, probably has race conditions
           if self.eof > 2 and hasattr(self,'notifier'):
              # this gets false positives for QProcess (which doesn't set notifier
              # but seems to be OK with file and stdin
              self.notifier.setEnabled(False)  # stop looking for more
              self.rebutton('Close', self.close,'eof={}'.format(self.eof))
        if b and len(b)>0:
            self.eof = 0
            t = b.decode('utf-8', errors='backslashreplace')
            # self.textbody.append(t)  # append adds an extra paragraph separator
            #self.endcursor.insertText(t)
            if self.opt.format=='h':  e.insertHtml(t)
            #WTF# elif self.opt.format=='m': e.insertMarkdown(t)
            else: e.insertText(t)
            if self.ui.followCheck.isChecked():
                self.textbody.setTextCursor(e)
        if b and len(b)==blocksize and not self.file.atEnd():
            self.want_read_more.emit('more')
        if self.firstRead and (self.eof>2 or e.position()>200 or self.textbody.document().blockCount()>10): # SETTING threshold
            # if never resized, resize at eof or 200 bytes or 10 lines
            # XXX but maybe not if there's more to read immediately??
            self.firstRead=False
            self.actionAdjust()
            rdelay = 0
            rdelay = typedQSettings().value('QTailDelayResize',3)
            if b and rdelay:
                #if typedQSettings().value('DEBUG',False):print("set timer to "+str(rdelay)) # DEBUG
                QTimer.singleShot(int(rdelay)*1000, Qt.VeryCoarseTimer, self.actionAdjust)
        self.showsize(False)

    # @QtCore.pyqtSlot(str)
    def filechanged(self, path):
        self.readtext('changed')
    # @QtCore.pyqtSlot(QSocketDescriptor, QsocketNotifier.Type)
    def socketActivated(self, socket):
        # XXX detect eof here???
        self.readtext('socket')
        
    def start(self):
        doc = self.textbody.document()
        doc.setMaximumBlockCount(self.opt.maxLines)
        # this will get run on some pass maybe
        if hasattr(self.opt, 'argparse'):
            if  self.opt.argparse.nowrap:
                # change it in both places
                self.ui.actionWrap_lines.setChecked(False)
                self.wrapChanged(False)
            if self.opt.argparse.autorefresh!=None:
                self.ui.actionAutorefresh.setChecked(True)
                if self.opt.argparse.autorefresh:
                    self.setWatchInterval(self.opt.argparse.autorefresh)

    def showsize(self, replace=True):
        m = self.statusBar().currentMessage()
        if m and not replace and 'lines' not in m:
            return
        self.statusBar().showMessage(str(self.textbody.document().blockCount())+" lines",-1)

    def simpleargs(self, args):
        # Process simple "command line" arguments from noacli internal parsing
        # only single word options supported, so --option=value must be used
        # ignore --file and --files (processed by caller)
        # Don't abort everything on errors, just pass the message along
        msg = None
        try:
            self.opt.processOptions(None,args)
        except argparse.ArgumentError as e:
            #print(repr(e)) # DEBUG
            msg = format("--{}: {}".format(e.args[0].dest, e.args[1]))
        except Exception as e:
            msg = str(e)
        finally:
            if msg:
                self.errmsg = msg # XX nobody uses this yet
                print('except: '+msg) # EXCEPT
                return (msg, -1)

        if typedQSettings().value('DEBUG',False) and hasattr(self.opt,'rest') and len(self.opt.rest)>1:
            print('Unparsed options: '+repr(self.opt.rest)) # ifDEBUG
            if '--rest' in self.opt.rest: # debug the debug
                print("parsed: "+repr(self.opt.argparse)) # ifDEBUG
        return

    def openfile(self,filename):
        self.filename = filename # reuse later?
        self.start()
        if self.opt.format=='m':
            self.openMarkdownFile(filename)
            return
        if self.opt.url:
            # bypass normal file I/O and let Qt do it
            self.file = None
            self.ui.textBrowser.setSource(QtCore.QUrl(filename))
            self.setButtonMode()
            return
        # XXX assume tail mode
        f = QtCore.QFile(filename)
        if not f.open(QtCore.QFile.ReadOnly):
            err = 'Open failed on {}: {}'.format(filename,f.errorString())
            print(err) # EXCEPT
            # clean up
            self.close()
            #self.setParent(None)
            self.deleteLater()
            # pyqt should have done something like this
            raise Exception(f.errorString())
        else:
            self.file = f
            self.opt.file = True

        if not self.opt.title:
            title=filename
            if len(title)>30: title=os.path.basename(title)
            self.setWindowTitle(title)
        self.reload();
        
        # follow the tail of the file
        self.watcher = QtCore.QFileSystemWatcher([filename])
        self.watcher.fileChanged.connect(self.filechanged)
        self.endcursor = self.textbody.textCursor()
        self.endcursor.movePosition(QtGui.QTextCursor.End)
        self.textbody.setTextCursor(self.endcursor)
    
    def openMarkdownFile(self, filename):
        # Qt textBrowser doesn't support appending to markdown so...
        # we break all the rules for this one
        #self.opt.format = 'm'
        self.filename = filename
        self.file = None
        try:
            f = open(filename)
            # XXX set filename and flag as markdown?
            text = f.read()
        except OSError:
            self.close()
            self.setParent(None)
            raise
        finally:
            f.close()
        self.setWindowTitle(filename)
        self.ui.textBrowser.document().setMarkdown(text)
        self.setButtonMode()

    def openstdin(self):
        self.start()
        self.setButtonMode()
        if not self.opt.title:
            self.setWindowTitle('qtail: stdin')
        # QFile doesn't work with readyRead, use QSocketNotifier instead for pipes
        f = QtCore.QFile()
        self.file = f
        f.open(sys.stdin.fileno(), QtCore.QFile.ReadOnly);
        os.set_blocking(sys.stdin.fileno(), False)  # XX not portable?
        #broken on File # self.file.readyRead.connect(self.readtext)

        # Attempt a socket notifier instead of readyread
        # seems to work equally well (in linux) on pipes and files
        n = QSocketNotifier(sys.stdin.fileno(), QSocketNotifier.Read, self)
        self.notifier = n
        self.socketconnection = n.activated.connect(self.socketActivated)
        self.errnotifier = QSocketNotifier(sys.stdin.fileno(), QSocketNotifier.Exception, self)

        self.opt.file = False  #XXX sometimes this might be a file
        #if typedQSettings().value('DEBUG',False):print("stdin") # DEBUG
        #self.reload();  # socket notifier makes this redundant
        
    def openProcess(self, title, process):
        self.start()
        self.file = process
        if not self.opt.title:
            self.setWindowTitle(title)
        self.opt.file = False
        self.setupProc()

    def setupProc(self):
        self.setButtonMode()
        if not self.file: return
        self.file.readyRead.connect(partial(self.readtext,'ready proc'))
        self.file.started.connect(self.procStarted)
        self.file.finished.connect(self.procFinished)

    def openPretext(self, jobitem, textstream, pretext='', title=None):
        self.start()
        # textstream seems broken for non-blocking I/O
        self.textbody.setPlainText(pretext)
        # someone else already initialized stuff, just handing it over
        # pretend like we did it
        self.jobitem = jobitem # take ownership
        jobitem.setWindow(self)
        self.file = jobitem.process
        # get a window title from somewhere
        if not title and jobitem:
            title = jobitem.title()
        if not title and jobitem.process:
            try:
                #c = process.program() # XX get args too?
                # as long as we always wrap in bash -c, just get the args
                # should set the title from a template in SETTINGs?
                c = " ".join(process.arguments()[1:])
                c = c.strip()
                c = c.partition('\n')[0]  # don't mess with multiple lines
                c = c.strip('#') # DOCUMENT default title!
                title=c[0:30] # truncate SETTING?
            except Exception as e:
                print(str(e)) # EXCEPT
        if not title:  # try again
            title='qtail: reopen'  # SETTING?
        self.setWindowTitle(title)
        self.opt.file = False
        self.setupProc()
        # these are likely too soon
        #self.actionAdjust()
        # if there's some text and it's big enough, or no more is coming...
        if pretext and (len(pretext)>200 or type(self.file)!=QProcess or self.file.state()==QProcess.NotRunning): # SETTING min size threshold
            self.want_resize.emit()
        #else: wait for data

    def procStarted(self):
        self.timestart = time.monotonic()
        self.setButtonMode()
        self.runcount += 1

    def procFinished(self, exitcode, estatus):
        if self.firstRead: self.actionAdjust()
        self.setButtonMode()
        self.timestop = time.monotonic()
        # calculate running average
        t = self.timestop-self.timestart
        if self.runtime==None: self.runtime=t
        self.runtime = self.runtime * 0.6 + t*0.4
        self.tweakInterval()
        if typedQSettings().value('DEBUG',False): print('runtime={:1.2f}s'.format(self.runtime))
        if self.ui.textBrowser.document().isEmpty():
            # XXX should close on empty be conditional?
            self.close()

    def terminateProcess(self, checked):
        self.file.terminate()
        self.rebutton('Kill harder', self.killProcess)

    def killProcess(self, checked):
        self.file.kill()
        self.rebutton('Close', self.close,'killed') # reassign when it dies

    def rebutton(self, label, slot, why=''):
        title = 'unknown'
        if hasattr(self,'jobitem'): title=self.jobitem.title()
        #print("rebutton {} = {} {}".format(title, label,why)) # DEBUG
        button = self.ui.reloadButton
        if self.buttonCon:
            # print("  unbutton {}".format(button.text())) # DEBUG
            self.disconnect(self.buttonCon)
        button.setText(label)
        self.buttonCon = button.clicked.connect(slot)

    def sizeHint(self):
        return QSize(100,100)
    
    @QtCore.pyqtSlot()
    def reload(self):
        if not self.file and hasattr(self, 'filename'):
            # try to reopen it
            self.textbody.clear()
            return self.openfile(self.filename)
        if self.file and self.opt.file:
            # back up 1M if we can (default)
            tailoff = self.opt.tailFrag
            # XXX whole is slow and eats memory if the file is too big!
            if not self.opt.whole:
                p = self.file.size()
            if not self.opt.whole and p > tailoff:
                self.file.seek(p-tailoff)
            else:
                # just go to the start
                self.file.seek(0)
            self.textbody.clear()
        else: # not a file, can't seek
            self.showsize()
        self.readtext('reload')

    # this can take either QAction or QCheckBox
    # checkbox was removed from UI main panel and moved into a menu
    @QtCore.pyqtSlot(bool)
    @QtCore.pyqtSlot(int)
    def wrapChanged(self, state):
        e = self.textbody.textCursor()
        if state:
            self.textbody.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.textbody.setLineWrapMode(QTextEdit.NoWrap)
        self.textbody.setTextCursor(e)

    ### settings that can change, trigger from UI elements
    # textBrowser.setLineWrapMode = WidgetWidth | NoWrap
    # text mode: html richtext markdown plain --> change insert function, reload
    # * setMarkdown() (clears text) ; features for varients
    # * setHtml setPlainText(QString body)
    # * setText --> guesses plain or html
    # * property plainText
    # append(QString)
    # edit->textCursor().insertHtml(QString) insertPlainText=cursor.insertText
    #  insert{Html,Table,Text}
    # textCursor() / setTextCursor() (get=copy/set visible)
    # cursor.movePosition(op, mode, anchor, num) op=(Start End) 
    # setKeepPositionOnInsert(bool)
    # clear()
    # setFontFamily setCurrentFont
    # find Qstring|RegEx
    # setMaximumBlockCount / blockCount()
    
    ### menu action slots
    @QtCore.pyqtSlot()
    def actionAdjust(self):
        doc = self.textbody.document()
        docrect = doc.size() # QsizeF
        rect= self.size()
        framedx = rect.width() - docrect.width()
        framedy = rect.height() - docrect.height()
        #print("ideal="+str(doc.idealWidth())+" width="+str(doc.textWidth())) # DEBUG
        # time this expensive function and don't do it again if it's bad
        if not self.disableAdjustSize:
            start = time.time()
            doc.adjustSize()
            interval = time.time()-start
            blocks = doc.blockCount()
            #print('adjustSize took {}s for {} blocks'.format(interval, blocks)) # DEBUG
            if interval > 0.5 or blocks>100:  # SETTING time and maxline threshold for resize
                # don't need to do this again if we have enough samples
                # or if it took too long this time
                self.disableAdjustSize=True
        #print(" ideal="+str(doc.idealWidth())+" width="+str(doc.textWidth())) # DEBUG
        newsize = doc.size()
        #print(' docsize='+str(newsize)) # DEBUG
        lay = self.textbody.document().documentLayout()
        #Abstract# print(' max='+str(lay.maximumWidth())+' min='+str(lay.minimumWidth())) # DEBUG
        ## try to pick a decent size
        height = docrect.height()
        width = docrect.width()
        #print(' docsize=%d,%d newsize=%d,%d'%(width,height,newsize.width(),newsize.height())) # DEBUG
        if height > newsize.height():
            height = newsize.height()
        if width<newsize.width() and width*1.5 > newsize.width():  # allow 50% growth
            width = newsize.width()*1.2 # Qt underesitmates
            #print('expand %d'%width) # DEBUG
        elif width > newsize.width(): # shrink
            width = newsize.width()
        width += framedx
        heightadjust = 100 # SETTING
        ## this was worse
        #if type(self.file)==QProcess and self.file.state()==QProcess.NotRunning:
        #    heightadjust = 0 # don't leave extra space if it is already dead
        if height > 50 and height < rect.height()*1.1:
            height += heightadjust   # guess at frame size
            #print('shrink height') # DEBUG
        else:
            # insane height was supplied
            height = rect.height()  # don't resize
        #print(' newsize='+str(width)+','+str(height)) # DEBUG
        self.resize(ceil(width), ceil(height))

##### end QtTail end
        
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # display
    QtCore.QCoreApplication.setOrganizationName("kg4ydw");
    QtCore.QCoreApplication.setApplicationName("QtTail");

    options = myOptions()
    args = options.processOptions(app)


    #if options.isCommand: # XXX not implemented yet


    mainwin = QtTail(options)
    if options.title: mainwin.setWindowTitle(options.title)
    
    w = mainwin.ui

    mainwin.show()
    mainwin.start()

    if options.isCommand:
        # save command for later reuse
        # open pipe
        # resize window with adjust() if command exits 
        pass
    elif args and args[0]!='-':
        mainwin.openfile(args[0])
    else:
        mainwin.openstdin()
    
    app.exec()
