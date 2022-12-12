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

import sys
import os
from functools import partial
from math import ceil

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QLineEdit, QActionGroup, QWidgetAction, QSpinBox, QAbstractSpinBox, QShortcut
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QSocketNotifier, QSize, QTimer, QProcess
from PyQt5.Qt import Qt, pyqtSignal

from qtail_ui import Ui_QtTail

from typedqsettings import typedQSettings

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
        # XX whole file mode vs tail mode?  oneshot vs. follow?
        # XX alternate format options: html markdown fixed-font

    def processOptions(self, app):
        parser = QCommandLineParser()
        parser.setApplicationDescription("View and follow the tail end of a file")
        parser.addHelpOption()
        # XXX parser.addVersionOption()

        optCommand = QCommandLineOption("command","view output from command")
        parser.addOption(optCommand)
        ## copy some options from tail, but not exactly
        optTailFrag = QCommandLineOption(['c', 'bytes'], 'maximum size of tail chunk in bytes', 'bytes', str(self.tailFrag))
        parser.addOption(optTailFrag)
        optLines = QCommandLineOption(['n', 'lines'], 'keep the last NUM lines', 'NUM')
        parser.addOption(optLines)
        optWhole = QCommandLineOption(['w','whole'], 'look at the whole file, not just the tail')
        parser.addOption(optWhole)
        optTitle = QCommandLineOption(['t','title'], 'set window title if a filename is not supplied','title')
        parser.addOption(optTitle)
        optFormat = QCommandLineOption(['format'], 'Pick a format (plaintext html)', 'format') # XX markdown doesn't work
        parser.addOption(optFormat)
        
        #XXX more options from tail
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
        
        parser.process(app)
        ## convert parsed options into sane and useful values
        self.isCommand = parser.isSet(optCommand)
        try: tailFrag = int(parser.value(optTailFrag))
        except: tailFrag = 0
        if tailFrag > 100: self.tailFrag = tailFrag
        try: lines = int(parser.value(optLines))
        except: lines = 0;
        if parser.isSet(optLines): self.maxLines = lines
        self.whole = parser.isSet(optWhole)
        if self.whole: self.maxLines = 0
        if parser.isSet(optTitle):
            self.title = parser.value(optTitle)
        if parser.isSet(optFormat):
            f = str(parser.value(optFormat))[0].lower()
            if f=='m': self.format='m'
            elif f=='h': self.format='h'
            else: self.format = None

        self.args = parser.positionalArguments()
        return self.args
                
class QtTail(QtWidgets.QMainWindow):
    window_close_signal = pyqtSignal()
    want_resize = pyqtSignal()
    want_read_more = pyqtSignal(str)
    have_error = pyqtSignal(str)
    def __init__(self, options=None, parent=None):
        super().__init__()
        self.eof = 0 # hack
        self.buttonCon = None
        dir = os.path.dirname(os.path.realpath(__file__))
        icon = QtGui.QIcon(os.path.join(dir,'qtail.png'))
        if icon.isNull() or len(icon.availableSizes())<1: # try again
            icon = QtGui.QIcon('qtail.png')
        self.setWindowIcon(icon)

        # connect to my own event so I can send myself a delayed signal
        self.want_resize.connect(self.actionAdjust, Qt.QueuedConnection) # delay this
        self.want_read_more.connect(self.readtext, Qt.QueuedConnection) # read more after everything else is updated

        if options==None:
            options=myOptions()
        self.firstRead = True
        self.opt = options
        self.ui = Ui_QtTail()
        self.ui.setupUi(self)
        self.textbody = self.ui.textBrowser
        # XXX findflags not used (yet?)
        self.findflags = 0  # QTextDocument::FindBackward FindCaseSensitively FindWholeWords
        self.findcount = 0;
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

    def getFontSetting(self, name):
        font = typedQSettings().value(name, None)
        if font and font.family():
            return font
        else:
            return None

    def setButtonMode(self):
        if type(self.file)==QProcess:
            if self.file.state()==QProcess.Running:
                self.rebutton('Kill', self.terminateProcess)
            elif self.ui.actionWatch.isChecked():
                self.rebutton('Rerun', self.reloadOrRerun)
            else:
                self.rebutton('Close', self.close)
        else: ## XXX distinguish between stdin and a file
            self.rebutton('Close', self.close)
        #else: # file
        #   self.rebuttion('Reload',self.reload)
        
    def setWatchInterval(self):
        val = self.ui.intervalLine.value()
        self.reinterval = val
            
    def actionAutoRefresh(self):
        checked = self.ui.actionAutorefresh.isChecked()
        if checked:
            self.timer.start(self.reinterval*1000)
        else:
            self.timer.stop()
            
    def reloadOrRerun(self):
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
        success = self.textbody.find(text)
        if success:
            self.findcount += 1
            es = self.textbody.extraSelections()
            self.statusBar().showMessage('Found {}/{}'.format(self.findcount, len(es)))
        else:
            # try again
            cursor = self.textbody.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            self.textbody.setTextCursor(cursor)
            success = self.textbody.find(text)
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
              self.rebutton('Close', self.close)
        if b and len(b)>0:
            self.eof = 0
            t = b.decode('utf-8', errors='backslashreplace') # XXX gets unicode errors, needs try
            # self.textbody.append(t)  # append adds an extra paragraph separator
            #self.endcursor.insertText(t)
            if self.opt.format=='h':  e.insertHtml(t)
            #WTF# elif self.opt.format=='m': e.insertMarkdown(t)
            else: e.insertText(t)
            if self.ui.followCheck.isChecked():
                self.textbody.setTextCursor(e)
        if b and len(b)==blocksize and not self.file.atEnd():
            self.want_read_more.emit('more')
        if self.firstRead and (self.eof>2 or e.position()>200 or self.textbody.document().blockCount()>10): # XXX SETTING threshold
            # if never resized, resize at eof or 200 bytes or 10 lines
            # XXX but maybe not if there's more to read immediately??
            self.firstRead=False
            self.actionAdjust()
            rdelay = 0
            rdelay = typedQSettings().value('QTailDelayResize',3)
            if b and rdelay:
                #if typedQSettings().value('DEBUG',False):print("set timer to "+str(rdelay)) # DEBUG
                QTimer.singleShot(int(rdelay)*1000, Qt.VeryCoarseTimer, self.actionAdjust)
            self.showsize()

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

    def showsize(self):
        self.statusBar().showMessage(str(self.textbody.document().blockCount())+" lines",-1)

    def simpleargs(self, args):
        # Process simple "command line" arguments from noacli internal parsing
        # only single word options supported, so --option=value must be used
        # XXXXX
        # ignore --file and --files (processed by caller)
        # --maxlines=
        return

    def openfile(self,filename):
        # XXX assume tail mode
        try:
            f = QtCore.QFile(filename)
            self.file = f
            f.open(QtCore.QFile.ReadOnly);
            self.opt.file = True
        except OSError as e:
            self.error = e.strerror
            err = 'Open failed on {}: {}'.format(filename,e.strerror)
            print(err) # EXCEPT
            # XXX send error somewhere
            self.have_error.emit(err)
            # clean up
            self.close()
            self.setParent(None)
            return err
        except Exception as e: # XXX what does Qt send?
            err = 'Error opening {}: {}'.format(filename, e)
            print(err)
            self.have_error.emit(err)
            self.close()
            self.setParent(None)
            return err

        if not self.opt.title:
            self.setWindowTitle(filename) # XXX qtail prefix? strip path?
        self.reload();
        
        # follow the tail of the file
        self.watcher = QtCore.QFileSystemWatcher([filename])
        self.watcher.fileChanged.connect(self.filechanged)
        self.endcursor = self.textbody.textCursor()
        self.endcursor.movePosition(QtGui.QTextCursor.End)
        self.textbody.setTextCursor(self.endcursor)

    def openstdin(self):
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
        self.file = process
        if not self.opt.title:
            self.setWindowTitle(title)
        self.opt.file = False
        self.file.readyRead.connect(partial(self.readtext,'ready proc'))
        self.rebutton('Kill', self.terminateProcess)
        self.file.finished.connect(self.procFinished)

    def openPretext(self, jobitem, textstream, pretext='', title=None):
        # textstream seems broken for non-blocking I/O
        self.textbody.setPlainText(pretext)
        # someone else already initialized stuff, just handing it over
        # pretend like we did it
        self.jobitem = jobitem # take ownership
        jobitem.setWindow(self)
        self.file = jobitem.process
        # get a window title from somewhere
        if not title and jobitem:
            title = jobitem.title
        if not title and process:
            try:
                #c = process.program() # XX get args too?
                # as long as we always wrap in bash -c, just get the args
                #XXX should set the title from a template in SETTINGs?
                c = " ".join(process.arguments()[1:])
                c = c.strip()
                c = c.partition('\n')[0]  # don't mess with multiple lines
                c = c.strip('#') # DOCUMENT default title!
                title=c[0:30] # truncate SETTING?
            except Exception as e:
                print(str(e)) # EXCEPT
        if not title:  # try again
            title='qtail: reopen'  # XXXX SETTING?
        self.setWindowTitle(title)
        self.opt.file = False
        if self.file:
            self.file.readyRead.connect(partial(self.readtext,'ready pre'))
            self.file.finished.connect(self.procFinished)
            self.setButtonMode()
        # these are likely too soon
        #self.actionAdjust()
        #self.showsize()
        if pretext and len(pretext)>200: # SETTING
            self.want_resize.emit()
        #else: wait for data

    def procFinished(self, exitcode, estatus):
        # XXX if exitcode: rebutton("Rerun", self.rerun)
        # self.rebutton('Close', self.close)
        if self.firstRead: self.actionAdjust()
        self.setButtonMode()
        if self.ui.textBrowser.document().isEmpty():
            # XXX should this be conditional?
            self.close()

    def terminateProcess(self, checked):
        self.file.terminate()
        self.rebutton('Kill harder', self.killProcess)

    def killProcess(self, checked):
        self.file.kill()
        self.rebutton('Close', self.close) # reassign when it dies

    def rebutton(self, label, slot):
        title = 'unknown'
        if hasattr(self,'jobitem'): title=self.jobitem.title()
        # print("rebutton {} = {}".format(title, label)) # DEBUG
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
        if self.opt.file:
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
        doc.adjustSize()  # XX this can be slow, avoid it when interacting?
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

    if options.isCommand:
        print('--Command not implemented yet')  # XXXX
        exit(1)

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
        # XXX handle multiple files later
        mainwin.openfile(args[0])
    else:
        mainwin.openstdin()
    
    app.exec_()
