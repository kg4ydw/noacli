
__license__   = 'GPL v3'
__copyright__ = '2022, Steven Dick <kg4ydw@gmail.com>'

# receiver window for small amounts of output, send to qtail if it gets big

import os
import sys
import re

from PyQt5 import QtCore
from PyQt5.Qt import pyqtSignal
from PyQt5.QtCore import QTimer, QSettings, QTextStream
from PyQt5.QtGui import QTextCursor, QImage, QTextOption, QPixmap
from PyQt5.QtWidgets import QTextBrowser

from typedqsettings import typedQSettings
from noajobs import jobItem
from qtail import QtTail

#import smalloutputres

#  transfer last command output to qtail if:
#    output exceeds visible lines
#    process exit timeout  ** not implemented
#    another command is run that produces output
#    user presses dup button (or shortcut?)
#  single line (or most recent?) output sent to status bar
#  don't remember more than visisible lines * 2 (option setting?)
#  option: disable small output window and send everything to qtail
#    auto
#    configured only (default qtail)
#    forced (disable auto-qtail)


## things to implement
# connect process
# set timeout
# read and count lines
# transfer to qtail
# clear buffer on next process
# reset max lines between processes if possible

class smallOutput(QTextBrowser):
    oneLine = pyqtSignal(str)
    newJobStart = pyqtSignal()
    sendToLog = pyqtSignal('PyQt_PyObject')
    buttonState = pyqtSignal(bool)
    gotNewLines = pyqtSignal(int)
    
    def __init__(self, parent):
        super(smallOutput,self).__init__(parent)
        self.keepState = False
        self.clearproc()  # zero out status stuff
        self.procCursor = None  # cursor
        self.jobitem = None
        # self.rawtext = None  # keep raw text for later use
        self.process = None
        self.jobitem = None
        self.procStartLine = 0
        self.outwinArgs = None
        px = QPixmap(301,2)
        if not px.loadFromData(b'P1\n301 2\n'+(b'1 0 '*302)):
            print('image fail') # EXCEPT
        self.lineImage = QImage(px)
        self.applySettings()
        # why can't designer set this?
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

    def applySettings(self):
        qs = typedQSettings()
        mul = qs.value('SmallMultiplier', 2)
        # if a fixed number is set, use it, otherwise delay this
        if mul>10 or mul<=0: # no max or fixed number of lines
            self.document().setMaximumBlockCount(mul)
        elif mul<10:
            num_lines = 10 # guess at the window size? decent default
            doc = self.document()
            if not doc: return  # just give up
            margin = doc.documentMargin()
            fm = self.fontMetrics().height()
            size = self.size() # what if it hasn't been shown yet?
            if fm and size and size.height():
                num_lines = (size.height() - 2*margin)/fm
            lines=int(num_lines * mul)+1
            self.document().setMaximumBlockCount(lines)
                
    ##### overrides
    def resizeEvent(self, event):
        super().resizeEvent(event)
        doc = self.document()
        margin = doc.documentMargin()
        num_lines = (event.size().height() - 2*margin)/self.fontMetrics().height()
        qs=typedQSettings()
        mul = qs.value('SmallMultiplier', 2)
        if mul>0 and mul<10:
            lines=int(num_lines * mul)+1
            #print('set max={} ({},{})'.format(lines,num_lines,mul)) # DEBUG
            self.document().setMaximumBlockCount(lines)
        elif mul>10:  # reset it just in case it was changed
            self.document().setMaximumBlockCount( mul)
        else:
            self.document().setMaximumBlockCount(0)  # no limit

    def contextMenuEvent(self, event):
        m=super().createStandardContextMenu(event.pos())
        m.addAction("Clear",self.clear)
        action = m.exec_(event.globalPos())

    ##### external signals

    @QtCore.pyqtSlot()
    def smallDup(self,more=''):
        self.gotNewLines.emit(-1)
        if not self.process and self.document().isEmpty():
            # allow duping a process that is dead
            # but not if there's no text either
            return
        # duplicate contents to a new top level small window (or qtail)
        ## alternate ways to get the old text
        #### grab everything
        #text = self.toPlainText()+more  # XXX only grab last process?
        #### grab process cursor -- process cursor isn't working right
        #c = self.getProcCursor()
        #text = c.selectedText()+more
        #c.removeSelectedText()
        ### make a new cursor based on procStartLine
        c = self.textCursor()
        c.movePosition(QTextCursor.Start)
        c.movePosition( QTextCursor.NextBlock, QTextCursor.MoveAnchor,self.procStartLine-1)
        c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        text = c.selectedText()+more
        c.removeSelectedText()

        # XXX if self.keepState leave a placeholder?
        self.disconnectProcess()

        if not self.jobitem: # internal command!
            title = 'internal'
            # construct a fake jobitem
            self.jobitem = jobItem(None)
            self.jobitem.setTitle('internal')
            self.jobitem.setMode('Internal')
            # add ourself to the job list since we're about to get a window
            if self.settings:
                self.settings.jobs.newjob(self.jobitem)
        else:
            self.jobitem.setMode('Tail')
            if self.jobitem:
                title = self.jobitem.title()
            elif self.process:
                title = self.process.command()[0] # XX
                self.jobitem.setTitle(title)
            else:
                title = 'dead' # XXX pull default? SETTING
        qt = QtTail(self.settings.qtail)
        qt.openPretext(self.jobitem, self.textstream, pretext=text, title=title)
        self.jobitem = None
        self.clearproc()

    @QtCore.pyqtSlot()
    def smallKill(self):
        if self.process:
            self.process.kill()
        else:
            self.oneLine.emit('Nothing to kill')
    @QtCore.pyqtSlot()
    def smallTerminate(self):
        if self.process:
            self.process.terminate()
        else:
            self.oneLine.emit('Nothing to kill')

    @QtCore.pyqtSlot()
    def smallLog(self):
        if not self.process: return
        # XX copy out old text first?
        self.disconnectProcess()
        # move process to log window and disconnect
        # pack up jobitem for easy passing
        self.jobitem.process = self.process
        self.jobitem.textstream = self.textstream
        self.sendToLog.emit(self.jobitem) # XXX pretext?
        self.clearproc()
        self.jobitem = None

    @QtCore.pyqtSlot(bool)
    def smallKeepToggle(self, checked):
        # if checked, clear immediately
        if not checked: self.clear()
        self.keepState = checked

    # used above
    def disconnectProcess(self):
        # disconnect a process prior to moving it somewhere else
        if self.process:
            self.process.readyRead.disconnect(self.readLines)
            self.process.finished.disconnect(self.procFinished)

    def clearproc(self):
        # these should have been saved somewhere else
        self.buttonState.emit(False)
        self.process = None
        self.textstream = None
        self.procCursor = None
        self.procStartLine = 0
        #self.jobitem = None   # maybe don't clear job item so fast

    ################
        
    def getProcCursor(self):
        if not self.procCursor:
            self.procCursor = self.textCursor()
            self.procCursor.movePosition(QTextCursor.End)
            # XXX alternately, find previous <hr> or move to start
        self.procCursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        return self.procCursor

    #### convenience functions
    def maxBlocks(self):
        return self.document().maximumBlockCount()
    def curBlock(self):
        return self.getProcCursor().blockNumber()
    
    ##### dunno if any of these are useful or correct yet
    def textLen(self):
        c = self.getProcCursor()
        return c.position() - c.anchor()

    def textBlockLen(self):
        b = getProcCursor()
        # not sure this is right
        a = self.textCursor().setPosition(b.anchor())
        return b.blockNumber() - a.blockNumber()
    def gettingFull(self,more=0):
        mx = self.maxBlocks()
        if mx>0:
            c= self.curBlock()+more-self.procStartLine # don't care about previous output
            #print("{}: {}>{}".format(mx,c,mx/2)) # DEBUG
            return c>mx/2
        return False
        #return self.maxBlocks()>0 and self.curBlock() +2 > self.maxBlocks()/2
    def countLines(self,t):
        return len(re.findall("\n", t))
    ################
    # process and I/O handling stuff

    # this class only handles process data, otherwise use qtail
    def openProcess(self, process, jobitem, settings):
        self.settings = settings  # need this for qtail
        if self.process: self.smallDup()
        if not self.keepState:
            self.clear()
        c = self.getProcCursor() # always do this just to intialize it
        if self.keepState:
            self.setTextCursor(c) # jump to end
        self.procStartLine = self.document().blockCount()
        self.jobitem = jobitem  # keep for later
        self.newJobStart.emit()
        self.process = process
        self.textstream = QTextStream(process)
        self.doneProc = False
        self.process.readyRead.connect(self.readLines)
        self.process.finished.connect(self.procFinished)
        self.buttonState.emit(True)
    
    def internalOutput(self, settings, msg):
        ## Accept output from internal commands
        # Note: do the normal thing if the previous was an internal command
        # otherwise, merge it and lose previous output
        if self.process:
            self.smallDup()
            if not self.keepState:
                self.clear()
        self.settings = settings
        # don't clear or dup for previous small output
        c = self.getProcCursor() # always do this just to intialize it
        self.setTextCursor(c) # jump to end
        self.procStartLine = self.document().blockCount()
        self.doneProc = True
        self.addLines(msg)
        
    def readLines(self):
        t = self.textstream.readAll()
        self.addLines(t)
        if self.doneProc:
            #print('last read') # DEBUG
            self.disconnectProcess()
            self.clearproc()  # really done now

    def addLines(self,t):
        # This bypasses clearing buffer from previous job, should not
        # be called externally, use internalOutput instead
        start = self.curBlock()
        emit = False
        if t:
            num = self.countLines(t)
            self.gotNewLines.emit(num)
            if num==1:
                self.oneLine.emit(t)
                emit = True
            if self.gettingFull(num):
                #print('full') # DEBUG
                self.smallDup(t)
            else:
                c = self.getProcCursor()
                c.insertText(t)
                self.setTextCursor(c)
            if self.visibleRegion().isEmpty() and not emit and start<self.curBlock():
                self.oneLine.emit('New output {} lines!'.format(self.curBlock()))
            else:
                # no status bar?
                pass
         
    def procFinished(self, exitcode, estatus):
        #print('small proc finished ') # DEBUG
        if not self.gettingFull(2):
            c = self.getProcCursor()
            # XX get time left / measured on timer
            if exitcode or self.document().isEmpty():
                c.insertHtml('<b>Exit {}</b><br/>'.format(exitcode))
            c.insertImage(self.lineImage)  # since <hr> is broken in QTextBrowser
            c.insertText("\n")
        # XX emit exit status if we didn't just send a line
        # emit anyway but keep it short (to append)
        if exitcode:
            self.oneLine.emit('E({})'.format(exitcode))
        else:
            self.oneLine.emit('(exit)')
        if self.process and self.process.bytesAvailable():
            self.doneProc = True # let readLines clean up
        else:
            self.disconnectProcess()
            self.clearproc()  # really done now
