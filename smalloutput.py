
# receiver window for small amounts of output, send to qtail if it gets big

import os
import sys
import re

from PyQt5 import QtCore
from PyQt5.Qt import pyqtSignal
from PyQt5.QtCore import QTimer, QSettings, QTextStream
from PyQt5.QtGui import QTextCursor, QImage, QTextOption
from PyQt5.QtWidgets import QTextBrowser

from typedqsettings import typedQSettings
from datamodels import jobItem
from qtail import QtTail

import smalloutputres

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
    
    def __init__(self, parent):
        super(smallOutput,self).__init__(parent)
        self.keepState = False
        self.clearproc()  # zero out status stuff
        self.procCursor = None  # cursor
        self.jobitem = None
        # self.rawtext = None  # keep raw text for later use
        self.process = None
        self.procStartLine = 0
        
        # apply settings
        qs = typedQSettings()
        mul = qs.value('SmallMultiplier', 2)
        # if a fixed number is set, use it, otherwise delay this
        if mul>10:
            self.document().setMaximumBlockCount(mul)
        # why can't designer set this?
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
            
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

    ##### external signals

    @QtCore.pyqtSlot()
    def smallDup(self,more=''):
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

        # XXX if self.keepState leave a placeholder
        self.disconnectProcess()
        if self.jobitem:
            title = self.jobitem.title()
        elif self.process:
            title = self.process.command()[0] # XX
            self.jobitem.setTitle(title)
        else:
            title = 'dead' # XXX pull default? SETTING
        
        qt = QtTail(self.settings.qtail)
        self.jobitem.setWindow(qt)
        qt.openPretext(self.process, self.textstream, pretext=text, title=title)
        self.clearproc()

    @QtCore.pyqtSlot()
    def smallKill(self):
        if self.process:
            self.process.kill()
        else:
            self.oneLine.emit('Nothing to kill')

    @QtCore.pyqtSlot()
    def smallLog(self):
        if not self.process: return
        # XX copy out old text first?
        self.disconnectProcess()
        # move process to log window and disconnect XXX
        self.clearproc()

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
        self.process = None
        self.textstream = None
        self.procCursor = None
        self.procStartLine = 0
        #self.jobitem = None   # maybe don't clear job item so fast

    ################

    def insertLine(self):
        c = self.textCursor()
        c.movePosition(QTextCursor.End)
        # work around bug that Qt won't fix
        # and none of these workarounds seem to help
        #blockFmt = c.blockFormat();
        #c.insertHtml("<hr/>") # XXX ugly, makes subsequent stuff underlined
        #c.insertText("\n>")
        c.insertHtml('<img src="line100.png" alt="----"/>')
        c.insertText("----\n")
        #c.setBlockFormat(blockFmt);
        #c.blockFormat().clearProperty(QTextFormat.BlockTrailingHorizontalRulerWidth);
        #self.setTextCursor(c)
        #c.insertHtml("<br/>")
        ##c.insertBlock(QTextBlockFormat());
        
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

        qs = typedQSettings()
        # XXX start oneshot timer
    
        
    def readLines(self):
        t = self.textstream.readAll()
        emit = False
        start = self.curBlock()
        if t:
            num = self.countLines(t)
            if num==1:
                self.oneLine.emit(t)
                emit = True
            if self.gettingFull(num):
                print('full') # DEBUG
                self.smallDup(t)
            else:
                c = self.getProcCursor()
                c.insertText(t)
                self.setTextCursor(c)
            if self.visibleRegion().isEmpty() and not emit and start<self.curBlock():
                self.oneLine.emit('New output {} lines!'.format(self.curBlock()))
            else:
                #print("no status bar: {} {} {}!<{}".format(self.isVisible(), emit, start, self.curBlock()))
                pass
                
        if self.doneProc:
            print('last read') # DEBUG
            self.disconnectProcess()
            self.clearproc()  # really done now
            
            
        pass # XXXX
    def procFinished(self, exitcode, estatus):
        print('small proc finished ') # DEBUG
        if not self.gettingFull(2):
            c = self.getProcCursor()
            # XXX get time left / measured on timer
            if exitcode:
                c.insertHtml('<b>Exit {}</b><br/>'.format(exitcode))
            #c.insertImage('<svg viewbox="0 0 200 1"><line x1="4" x2="100%" y1="0" y2="1" stroke="black" stroke-width="1" /></svg>')
            #c.insertImage(QImage(':line100.pbm'))
            c.insertImage(QImage(':line.svg'))
            #c.insertHtml('<img src="line100.png" alt="----" />')
            c.insertText("\n")
        # XXX emit exit status if we didn't just send a line
        # emit anyway but keep it short (to append)
        if exitcode:
            self.oneLine.emit('E({})'.format(exitcode))
        else:
            self.oneLine.emit('(exit)')
        if self.process.bytesAvailable():
            self.doneProc = True # let readLines clean up
        else:
            self.disconnectProcess()
            self.clearproc()  # really done now


    def timeoutProc():
        pass # XXXX
