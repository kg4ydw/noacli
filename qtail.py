#!/usr/bin/env python3

import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextEdit, QSizePolicy
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice
from qtail_ui import Ui_QtTail
from math import ceil

# options values -- set defaults
class myOptions():
    def __init__(self):
        self.maxLines = 10000
        self.tailFrag = 1000*1000
        # note: maxLines*80 is close to tailFrag
        self.isCommand = False
        self.file = False
        self.whole = False
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

        self.args = parser.positionalArguments()
        return self.args

class QtTail(QtWidgets.QMainWindow):
    def __init__(self, options):
        super(QtTail,self).__init__()
        self.opt = options
        self.ui = Ui_QtTail()
        self.ui.setupUi(self)
        self.textbody = self.ui.textBrowser
        self.findflags = 0  # QTextDocument::FindBackward FindCaseSensitively FindWholeWords
        if self.opt.maxLines>0:
            self.textbody.document().setMaximumBlockCount(self.opt.maxLines)

    @QtCore.pyqtSlot(str)
    def simpleFind(self, text):
        success = self.textbody.find(text)
        if success:
            self.statusBar().showMessage('found')
        else:
            self.statusBar().showMessage('not found')

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
            e.insertText(t)
            if self.ui.followCheck.isChecked():
                self.textbody.setTextCursor(e)
            self.showsize()

    # @QtCore.pyqtSlot(str)
    def filechanged(self, path):
        # XXX do something if there are multiple files
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
        self.reload();
        
        # follow the tail of the file
        self.watcher = QtCore.QFileSystemWatcher([filename])
        self.watcher.fileChanged.connect(self.filechanged)
        self.endcursor = self.textbody.textCursor()
        self.endcursor.movePosition(QtGui.QTextCursor.End)
        self.textbody.setTextCursor(self.endcursor)

    def openstdin(self):
        f = QtCore.QFile()
        self.file = f
        f.open(0, QtCore.QFile.ReadOnly);
        self.textstream = QtCore.QTextStream(f)
        self.opt.file = False  #XXX sometimes this might be a file
        print("stdin")
        self.reload();
        
        # XXX set event handlers
        self.file.readyRead.connect(self.readtext)
        

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
        print("ideal="+str(doc.idealWidth())+" width="+str(doc.textWidth()))
        doc.adjustSize()
        print(" ideal="+str(doc.idealWidth())+" width="+str(doc.textWidth()))
        print(' page='+str(doc.pageSize()))
        newsize = doc.size()
        print(' docsize='+str(newsize))
        lay = self.textbody.document().documentLayout()
        #Abstract# print(' max='+str(lay.maximumWidth())+' min='+str(lay.minimumWidth()))
        ## try to pick a decent size
        height = docrect.height()
        width = docrect.width()
        print(' docsize='+str(width)+','+str(height))
        if height > newsize.height():
            height = newsize.height()
        if width < newsize.width()*0.80:  # allow 20% growth
            width = newsize.width()*1.2 # Qt underesitmates
        elif width > newsize.width(): # shrink
            width = newsize.width()
        width += framedx
        if height > 50 and height < rect.height():
            height += 100   # guess at frame size
            print('shrink height')
        else: height = rect.height()  # don't resize
        print(' newsize='+str(width)+','+str(height))
        self.resize(ceil(width), ceil(height))
        
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # display
    #XXX QtCore.QCoreApplication.setOrganizationName("ssdApps");
    QtCore.QCoreApplication.setApplicationName("QtTail");

    options = myOptions()
    args = options.process(app)

    if options.isCommand:
        print('--Command not implemented yet')
        exit(1)

    mainwin = QtTail(options)
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

    
    
