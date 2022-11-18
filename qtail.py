#!/usr/bin/env python3

import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextEdit, QSizePolicy
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QSocketNotifier, QSize
from PyQt5.Qt import Qt, pyqtSignal

from math import ceil

from qtail_ui import Ui_QtTail

import qtailres

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
        # whole file mode vs tail mode?  oneshot vs. follow?
        # alternate format options: html markdown fixed-font

    def process(self, app):
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
    def __init__(self, options=None, parent=None):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon(':qtail.png'))
        # connect to my own event so I can send myself a delayed signal
        self.want_resize.connect(self.actionAdjust, Qt.QueuedConnection) # delay this

        if options==None:
            options=myOptions()
        self.firstRead = True
        self.opt = options
        self.ui = Ui_QtTail()
        self.ui.setupUi(self)
        self.textbody = self.ui.textBrowser
        # XXX findflags not used
        self.findflags = 0  # QTextDocument::FindBackward FindCaseSensitively FindWholeWords
        self.findcount = 0;
        if self.opt.maxLines>0:
            self.textbody.document().setMaximumBlockCount(self.opt.maxLines)

    def closeEvent(self,event):
        self.window_close_signal.emit()
        super().closeEvent(event)

    @QtCore.pyqtSlot(str)
    def simpleFind(self, text):
        start = self.textbody.textCursor()
        success = self.textbody.find(text)
        if success:
            self.findcount += 1
            self.statusBar().showMessage('Found '+str(self.findcount))
        else:
            # try again
            cursor = self.textbody.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            self.textbody.setTextCursor(cursor)
            success = self.textbody.find(text)
            if success:
                if self.findcount:
                    m = 'Wrapped after '+str(self.findcount)
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
    def readtext(self):
        t = self.textstream.readAll()
        if t:
            # self.textbody.append(t)  # append adds an extra paragraph separator
            #self.endcursor.insertText(t)
            e = self.textbody.textCursor()
            e.movePosition(QtGui.QTextCursor.End)
            if self.opt.format=='h':  e.insertHtml(t)
            #WTF# elif self.opt.format=='m': e.insertMarkdown(t)
            else: e.insertText(t)
            if self.ui.followCheck.isChecked():
                self.textbody.setTextCursor(e)
            if self.firstRead:
                self.firstRead=False
                self.actionAdjust()
            self.showsize()

    # @QtCore.pyqtSlot(str)
    def filechanged(self, path):
        # XXX do something if there are multiple files
        self.readtext()
    # @QtCore.pyqtSlot(QSocketDescriptor, QsocketNotifier.Type)
    def socketActivated(self,socket):  # ,type):
        self.readtext()

    def start(self):
        doc = self.textbody.document()
        doc.setMaximumBlockCount(self.opt.maxLines)
        # XXX initialize other stuff?

    def showsize(self):
        self.statusBar().showMessage(str(self.textbody.document().blockCount())+" lines",0)

    def openfile(self,filename):
        # XXX assume tail mode
        f = QtCore.QFile(filename)
        self.file = f
        f.open(QtCore.QFile.ReadOnly);
        self.textstream = QtCore.QTextStream(f)
        self.opt.file = True
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
        # XXX File doesn't work with readyRead
        f = QtCore.QFile()
        self.file = f
        f.open(0, QtCore.QFile.ReadOnly);
        os.set_blocking(0, False)  # XX not portable?
        self.textstream = QtCore.QTextStream(f)
        #broken on File # self.file.readyRead.connect(self.readtext)

        # Attempt a socket notifier instead of readyread
        # seems to work equally well (in linux) on pipes and files
        n = QSocketNotifier(0, QSocketNotifier.Read, self)
        self.notifier = n
        n.activated.connect(self.socketActivated)

        self.opt.file = False  #XXX sometimes this might be a file
        print("stdin") # DEBUG
        #self.reload();  # socket notifier makes this redundant
        
    def openProcess(self, title, process):
        self.file = process
        if not self.opt.title:
            self.setWindowTitle(title)
        self.textstream = QtCore.QTextStream(process)
        self.opt.file = False
        self.file.readyRead.connect(self.readtext)
        self.rebutton('Kill', self.killProcess)
        self.file.finished.connect(self.procFinished)

    def openPretext(self, process, textstream, pretext='', title=None):
        self.textbody.setPlainText(pretext)
        # someone else already initialized stuff, just handing it over
        # pretend like we did it
        self.file = process
        # get a window title from somewhere
        if not title: title='qtail: reopen'  # XXXX setting?
        self.setWindowTitle(title)
        self.textstream = textstream
        self.opt.file = False
        if self.file:
            self.file.readyRead.connect(self.readtext)
            self.rebutton('Kill', self.killProcess)
            self.file.finished.connect(self.procFinished)
        # these are likely too soon
        #self.actionAdjust()
        #self.showsize()
        # can I emit my own signal?
        # s= pyqtSignal()
        if pretext:
            self.want_resize.emit()
        #else: wait for data

    def procFinished(self, exitcode, estatus):
        # XXX if exitcode: rebutton("Rerun", self.rerun)
        self.rebutton('Close', self.close)
        if self.ui.textBrowser.document().isEmpty():
            # XXX should this be conditional?
            self.close()

    def killProcess(self, checked):
        self.file.kill()
        self.rebutton('Close', self.close)
        # XXX or rerun?

    def rebutton(self, label, slot):
        button = self.ui.reloadButton
        button.setText(label)
        button.clicked.disconnect()
        button.clicked.connect(slot)

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
        self.readtext()

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
        doc.adjustSize()
        #print(" ideal="+str(doc.idealWidth())+" width="+str(doc.textWidth())) # DEBUG
        newsize = doc.size()
        #print(' docsize='+str(newsize)) # DEBUG
        lay = self.textbody.document().documentLayout()
        #Abstract# print(' max='+str(lay.maximumWidth())+' min='+str(lay.minimumWidth())) # DEBUG
        ## try to pick a decent size
        height = docrect.height()
        width = docrect.width()
        #print(' docsize='+str(width)+','+str(height)) # DEBUG
        if height > newsize.height():
            height = newsize.height()
        if width < newsize.width()*0.80:  # allow 20% growth
            width = newsize.width()*1.2 # Qt underesitmates
        elif width > newsize.width(): # shrink
            width = newsize.width()
        width += framedx
        if height > 50 and height < rect.height()*1.1:
            height += 100   # guess at frame size
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
    #XXX QtCore.QCoreApplication.setOrganizationName("ssdApps");
    QtCore.QCoreApplication.setApplicationName("QtTail");

    options = myOptions()
    args = options.process(app)

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
